import os.path
import re
import contextlib
from collections import OrderedDict

def fill_out_template(dest_file, template_file, **variables):
	# fill out a template file
	if not os.path.isabs(template_file):
		template_file = os.path.join(root_dir, 'templates', template_file)
	with open(template_file) as fp:
		template = fp.read()

	text = template % variables
	
	# strip template comments
	text = re.sub(r'^#--.*\n', r'', text, flags=re.MULTILINE)

	with open(dest_file, 'w') as fp:
		fp.write(text)

def create_yaml_list(elems, SEP='\n    - '):
	return (SEP + SEP.join(elems)) if elems else ''

def load_manifest(fn):
	prefix_build = 'build:'

	# is fn a reference to a tag in versiondb (something like 'build:b1497')?
	if fn.startswith(prefix_build):
		url = 'https://raw.githubusercontent.com/lsst/versiondb/master/manifests/%s.txt' % fn[len(prefix_build):]
		import urllib2
		print url
		with contextlib.closing(urllib2.urlopen(url)) as fp:
			lines = fp.read().split('\n')
	else:
		# a regular file
		with open(fn) as fp:
			lines = fp.read().split('\n')

	def parse_manifest_lines(lines):
		for line in lines:
			line = line.strip()
			if not line:
				continue
			if line.startswith('#'):
				continue

			try:
				(product, sha, version, deps) = line.split()
				deps = deps.split(',')
			except ValueError:
				(product, sha, version) = line.split()
				deps = []

			yield (product, sha, version, deps)

	build_id = None
	if lines[1].startswith('BUILD='):
		build_id = lines[1][len('BUILD='):]

	return build_id, list( parse_manifest_lines(lines[2:]) )

def build_manifest_for_products(top_level_products, manifestFnOrId):
	# Load the manifest. Returns the OrderedDict and a set of EUPS tags
	# to associate with the manifest

	products = {}
	build_id, manifest_lines = load_manifest(manifestFnOrId)
	for (product, sha, version, deps) in manifest_lines:
		products[product] = (product, sha, version, deps)

	# Extract the products of interest (and their dependencies)
	manifest = OrderedDict()
	def bottom_up_add_to_manifest(product):
		(product, sha, version, deps) = products[product]
		for dep in deps:
			bottom_up_add_to_manifest(dep)
		if product not in manifest:
			manifest[product] = products[product]

	for product in top_level_products:
		bottom_up_add_to_manifest(product)

	return manifest, [ build_id ] if build_id is not None else []
