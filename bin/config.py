import os.path
import platform
import re
import sys
import fnmatch

import yaml

class Config(object):
	# Output directory where the package specs will be generated (as well as the rebuild script)
	# DANGER, DANGER: Be careful what you set this to -- it will be 'rm -rf'-ed !!!
	#
	# string, mapped from config.output_dir
	output_dir = None

	#
	# Directory with additional recipes, to satisfy any injected dependencies.
	# These are most often conda packages for packages out of PyPI, typically
	# generated using conda-skeleton.
	#
	additional_recipes_dir = None

	# Products that already exist in Anaconda; we'll skip building those (but will depend on them)
	#
	# list, loaded from config.internal_products
	internal_products = None

	# Numpy version to require (otherwise conda gets confused and sometimes tries to build some
	# packages against (e.g.) 1.9 and others against 1.10, leading to build failures)
	#
	# Hardcoded hacks (FIXME)
	##numpy_version = "numpy ==1.9"
	swig_version = "swig ==3.0.2"

	# Products to skip alltogether (i.e., don't build, don't make a dependency)
	#
	# list, mapped from config.skip_products
	skip_products = None

	# Products that need to be prefixed with our prefix to avoid collisions
	# Products whose Conda name will _not_ be prefixed with out namespace prefix
	#
	# set, union of config.dont_prefix_products and internal_products
	dont_prefix_products = None
	
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

	def conda_name_for(self, product, prefix=None, namemap=None, dontprefix=None):
		#
		# Return a conda product name, given an EUPS product name
		#

		if prefix is None:
			prefix = self.lsst_prefix
		if namemap is None:
			namemap = self.eups_to_conda_map
		if dontprefix is None:
			dontprefix = self.dont_prefix_products

		# return the conda package name for a product
		try:
			return namemap[product]
		except KeyError:
			pass

		transformed_name = product.replace('_', '-')
		transformed_name = transformed_name.lower()

		if product in dontprefix:
			return transformed_name
		else:
			return prefix + transformed_name

	def get_giturl(self, productName):
		# Find first remote in whose list of product globs there's
		# at least one that our productName matches
		for remote, productNameGlobs in self.git_upstreams.items():
			if next((glob for glob in productNameGlobs if fnmatch.fnmatch(productName, glob)), None):
				return remote % { 'product': productName }

	def __init__(self, fn):
		# Load the configuration file (YAML), do any necessary parsing
		# and variable substitutions, and return the result
		with open(fn) as fp:
			config = yaml.load(fp)

		# Expand eups->conda map
		for eups_name, conda_name in config['eups_to_conda_map'].items():
			config['eups_to_conda_map'][eups_name] = conda_name % config

		# Convert conda/foo -> (conda, foo) in dependencies
		_deps = {}
		for productName, deps in config['dependencies'].items():
			if '/' in productName:
				name_type, productName = productName.split('/')
			else:
				name_type = 'eups'

			if name_type == 'eups':
				productName = self.conda_name_for(productName, config['lsst_prefix'], config['eups_to_conda_map'], config['dont_prefix_products'])
			elif name_type == 'conda':
				pass
			else:
				raise Exception("Unknown name type, %s, when specifying the dependency for %s" % (name_type, productName))

			_deps[productName] = {}
			for type_ in ['run', 'build']:
				if type_ in deps:
					newDeps = []
					for (pkgType, pkgName) in (s.split('/') for s in deps[type_]):
						if pkgType == 'eups':
							assert ' ' not in pkgName
							pkgName = self.conda_name_for(pkgName, config['lsst_prefix'], config['eups_to_conda_map'], config['dont_prefix_products'])
						newDeps.append((pkgType, pkgName))
					_deps[productName][type_] = newDeps
		config['dependencies'] = _deps

		# Set member variables
		self.output_dir = os.path.abspath(config['output_dir'])
		self.additional_recipes_dir = os.path.abspath(config['additional_recipes_dir'])
		self.internal_products = set(config['internal_products'])
		self.skip_products = set(config['skip_products'])

		# Naming-related
		self.eups_to_conda_map = config['eups_to_conda_map']
		self.lsst_prefix = config['lsst_prefix']
		self.dont_prefix_products = set(config['dont_prefix_products']) | self.internal_products

		# Version hacks
		##self.numpy_version = "numpy ==1.9"
		self.swig_version = "swig ==3.0.2"

		# Dependencies
		self.missing_deps = { prodName: deps['build'] for prodName, deps in config['dependencies'].iteritems() }

		self.global_eups_tags = [ 'current' ]

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

