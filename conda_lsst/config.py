import os.path
import platform
import re
import sys
import fnmatch

import yaml

def expand_path(root, fragment):
	if not os.path.isabs(fragment):
		return os.path.join(root, fragment)
	return fragment

def merge(config, default):
	#
	# Merge the 'default' dict into 'config'
	# based on: http://stackoverflow.com/questions/823196/yaml-merge-in-python
	#
	if isinstance(config, dict) and isinstance(default, dict):
		for k, v in default.iteritems():
			if k not in config:
				config[k] = v
			else:
				config[k] = merge(config[k], v)
	return config

class Config(object):
	# Output directory where the package specs will be generated (as well as the rebuild script)
	# DANGER, DANGER: Be careful what you set this to -- it will be 'rm -rf'-ed !!!
	#
	# string, mapped from config.output_dir
	output_dir = None

	# The directory where the database with the hashes of recipes is cached, so that packages
	# don't have to be rebuilt if they already exist on some channel.
	#
	# string, mapped from config.recipe_db_dir
	recipe_db_dir = None

	#
	# Directory with additional recipes, to satisfy any injected dependencies.
	# These are most often conda packages for packages out of PyPI, typically
	# generated using conda-skeleton.
	#
	additional_recipes_dir = None

	#
	# Directory where the recipe templates are.
	#
	template_dir = None

	#
	# Directory where the product patches are.
	#
	patch_dir = None

	# Products that already exist in Anaconda; we'll skip building those (but will depend on them)
	# This is a dictionary, with value optionally containing another dictionary with
	# conda package specification for build and run clauses in meta.yaml. If the value is None
	# conda_name_for() will be used to deduce the conda name.
	#
	# dict( eupsName -> { 'build': 'package spec', 'run': 'package spec' }
	internal_products = None

	# Products to skip alltogether (i.e., don't build, don't make a dependency)
	#
	# list, mapped from config.skip_products
	skip_products = None

	# Products to skip building on certain platforms. The recipes will still be
	# generated.
	#
	# dict( conda_name ->  [ list of platforms ]), mapped from config.skip-build
	skip_build = None

	# Prefix to prepend to every conda product name (typically, 'lsst-')
	#
	# string
	lsst_prefix = None

	# A specific mapping between an EUPS product name and Conda product name. Takes
	# precedence over automatic prefixing.
	#
	# dict( eupsName -> condaName), mapped from config.eups_to_conda_map
	eups_to_conda_map = None

	# Missing dependencies (these would be transparently installed with pip otherwise)
	#
	# dict( condaName -> [ condaName1, condaName2, ... ] ), mapped from config.dependencies.build
	missing_deps = None

	# The EUPS tags to apply to all products build in this run
	# You should always leave 'current' so that when a new package is installed
	# it will become the default one that is set up.
	global_eups_tags = None

	# Patterns to find upstream repositories
	#
	# dict( upstream_url_pattern -> [ productGlob1, productGlob2, ... ] ), mapped from config.git-upstreams
	git_upstreams = None

	# Override SHA1s
	#
	# list of ( 'product_name' -> 'SHA1-or-ref' ), mapped from config.override_gitrev
	override_gitrev = None

	#
	# Conda channels where LSST packages are. These will be checked for previous versions
	# of LSST packages and indexed in the repo-cache directory.
	#
	# The actual channels are obtained by running this regex against the channels in .condarc
	#
	our_channel_regex = None

	#
	# The upload destination (server, dir on server, conda on server) for 'conda-lsst upload'
	# This should map to the directory accessible with the regex above
	#
	channel_server       = None
	channel_dir_base     = None
	channel_server_conda = None

	#
	# You should not need to manipulate this; change our_channel_regex instead
	# channel URLs
	channels = None

	# channel names
	channel_names = None

	platform = None
	uname = None

	def conda_name_for(self, product):
		#
		# Return a conda product name, given an EUPS product name
		#

		# return the conda package name for a product
		try:
			return self.eups_to_conda_map[product]
		except KeyError:
			pass

		transformed_name = product.replace('_', '-')
		transformed_name = transformed_name.lower()

		# don't prefix internal (aka system) products that don't
		# have explicit mappings to their conda names
		if product in self.internal_products:
			return transformed_name

		return self.lsst_prefix + transformed_name

	def get_giturl(self, productName):
		# Find first remote in whose list of product globs there's
		# at least one that our productName matches
		for remote, productNameGlobs in self.git_upstreams.items():
			if next((glob for glob in productNameGlobs if fnmatch.fnmatch(productName, glob)), None):
				return remote % { 'product': productName }

	def get_missing_deps(self, productName, typ):
		# Find all keys in self.missing_deps that match productName
		# Then return the union of all dependencies of the matching type
		# (note: returns a generator)
		matching = [ deps.get(typ, []) for glob, deps in self.missing_deps.items() if fnmatch.fnmatch(productName, glob) ]

		from itertools import chain
		return chain.from_iterable(matching)

	def __init__(self, root_dir, fns):
		# Load the configuration file (YAML), do any necessary parsing
		# and variable substitutions, and return the result

		# Load and merge all configuration files
		config = {}
		for fn in fns:
			try:
				with open(expand_path(root_dir, fn)) as fp:
					merge(config, yaml.load(fp))
			except IOError:
				pass

		# Expand eups->conda map
		for eups_name, conda_name in config['eups_to_conda_map'].items():
			config['eups_to_conda_map'][eups_name] = conda_name % config

		# Naming-related
		self.eups_to_conda_map = config['eups_to_conda_map']
		self.lsst_prefix = config['lsst_prefix']

		pv = config['pin_versions']

		# A mapping from LSST eups packages that will be replaced by conda equivalents
		# Apply pinned versions (if any) to entries that don't have a version specified
		self.internal_products = config['internal_products']
		for name, meta in self.internal_products.items():
			if name not in pv:
				continue

			if meta is None:
				meta = {}
			for typ in ('run', 'build'):
				pkgSpec = meta.get(typ, name)
				if len(pkgSpec.strip().split()) == 1: # name only ?
					meta[typ] = "%s %s" % (pkgSpec, pv[name][typ])

			self.internal_products[name] = meta

		# Parse system-provided dependencies specifications
		_deps = {}
		pv = config['pin_versions']
		for productName, deps in config['dependencies'].items():
			#
			# By default, the key is an EUPS name, but allow it to be a
			# conda name as well
			#
			if '/' in productName:
				name_type, productName = productName.split('/')
			else:
				name_type = 'eups'

			if name_type == 'eups':
				productName = self.conda_name_for(productName)
			elif name_type == 'conda':
				pass
			else:
				raise Exception("Unknown name type, %s, when specifying the dependency for %s" % (name_type, productName))

			#
			# By default, the values are conda names, but allow them to be
			# EUPS names as well.
			#
			_deps[productName] = {}
			for type_ in ['run', 'build']:
				if type_ in deps:
					newDeps = []
					for depSpec in deps[type_]:
						# Parse '[type/]name [verspec] [#selector]'
						res = re.match(r'^(?:(\w+)/)?((\S+)(?:\s+([^ ]+)(?:\s+(#.*))?)?)', depSpec)
						pkgType, pkgSpec, pkgName, verSpec, selector = res.groups()
						#print "XXXX", (pkgType, pkgSpec, pkgName, verSpec, selector)
						if pkgType == 'eups':
							assert ' ' not in pkgName
							pkgName = self.conda_name_for(pkgName)

						# Apply version pinning, if any
						if verSpec is None and selector is None and pkgName in pv:
							verSpec = pv[pkgName].get(type_, None)
							pkgSpec = "%s %s" % (pkgName, verSpec)
							#print "HERE: ", productName, type_, (pkgType, pkgName, verSpec, selector, pkgSpec)

						newDeps.append((pkgType, pkgName, verSpec, selector, pkgSpec))
					_deps[productName][type_] = newDeps
		config['dependencies'] = _deps

		# Set member variables
		self.output_dir = expand_path(root_dir, config['output_dir'])
		self.recipe_db_dir = expand_path(root_dir, config['recipe_db_dir'])
		self.additional_recipes_dir = expand_path(root_dir, config['additional_recipes_dir'])
		self.template_dir = expand_path(root_dir, config['template_dir'])
		self.patch_dir = expand_path(root_dir, config['patch_dir'])
		self.skip_products = set(config['skip_products'])
		self.skip_build = config.get('skip-build', {})

		# Dependencies
		self.missing_deps = config['dependencies']

		self.global_eups_tags = [ 'current', 'conda' ]

		# obtaining the source
		self.git_upstreams = config['git-upstreams']
		self.override_gitrev = config['override_gitrev']

		# Upload support
		self.channel_server       = config['upload']['server']
		self.channel_dir_base     = config['upload']['dir_base']
		self.channel_server_conda = config['upload']['conda']

		# Conda channel management
		self.our_channel_regex = config['our_channel_regex']

		from conda_build.config import croot
		# channel URLs
		self.channels = [
			'file://%s/' % croot,
		] + _get_our_channels(self.our_channel_regex)

		# channel names
		self.channel_names = _get_our_channel_names(self.our_channel_regex, self.channels)

		# Conda ID for the platform
		self.platform = "%s-%s" % ('osx' if sys.platform == 'darwin' else 'linux', platform.architecture()[0][:2])
		self.uname = sys.platform.title()

######################################################

def _get_our_channels(regex):
	""" Return channels from .condarc that match regex """
	from urlparse import urljoin
	import conda.config

	chans = [ urljoin(conda.config.channel_alias, u).rstrip('/ ') + '/' for u in conda.config.get_rc_urls() ]
	chans = [ chan for chan in chans if re.match(regex, chan) ]
	return chans

def _get_our_channel_names(regex, channels):
	def aux():
		for chan in channels:
			match = re.match(regex, chan)
			if not match:
				continue
			yield match.group(1)
	return list(aux())

