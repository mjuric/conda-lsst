import re
import subprocess
import os

# The path to the extract-version utility, computed as relative to this scripts' path
extract_version_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'scripts', 'extract-version')

def eups_to_conda_version(product, eups_version, giturl):
	# Convert EUPS version string to Conda-compatible pieces
	#
	# Conda version has three parts:
	#	version number: a version number that should be something Conda can parse and order
	#	build string: not used in version comparison, can be anything
	#	build number: if two versions are equal, build number is used to break the tie
	#
	#  Furthermore, it parses the version itself as described in the VersionOrder object docstring at:
	#      https://github.com/conda/conda/blob/master/conda/resolve.py
	#  We do our best here to fit into that format.

	# hardcoded for now. This should be incremented on a case-by-case basis to
	# push fixes that are Conda-build related
	buildnum = 0

	# Split into version + eups build number ("plusver")
	if '+' in eups_version:
		raw_version, plusver = eups_version.split('+')
		plusver = int(plusver)
	else:
		raw_version, plusver = eups_version, 0

	# Parse EUPS version:
	# Possibilities to detect:
	#	<vername>-<tagdist>-g<sha1>		-> (<vername>.<tagdist>, <plusver>_<sha1>, <buildnum>)
	#          <vername> can be <version>.lsst<N>	->   <vername>.<N>
	#	<branch>-g<sha1>			-> (<branch>_g<sha1>, <plusver>_<sha1>, <buildnum>)
	#	<something_completely_different>	-> (<something_completely_different>, '', <buildnum>)
	#

	def parse_full_version(version, giturl):	
		match = re.match('^([^-]+)-([0-9]+)-g([0-9a-z]+)$', version)
		if not match: return None, None

		vername, tagdist, sha1  = match.groups()

		# handle 1.2.3.lsst5 --> 1.2.3.5
		fixed_ver, _ = parse_lsst_patchlevel(vername, giturl)
		if fixed_ver is not None:
			vername = fixed_ver

		return "%s.%s" % (vername, tagdist), sha1

	def parse_lsst_patchlevel(version, giturl):
		# handle 1.2.3.lsst5 --> 1.2.3.5
		match = re.match(r'^(.*?).?lsst([0-9]+)$', version)
		if not match: return None, None

		true_ver, lsst_patch = match.groups()
		return "%s.%s" % (true_ver, lsst_patch), ''

	def parse_branch_sha1(version, giturl):
		match = re.match('^([^-]+)-g([0-9a-z]+)$', version)
		if not match: return None, None

		branch, sha1 = match.groups()
		
		timestamp = subprocess.check_output([extract_version_path, giturl, sha1]).strip()
		version = "%s.%s" % (branch, timestamp)

		return version, sha1

	def parse_default(version, giturl):
		return version, ''

	parsers = [ parse_full_version, parse_lsst_patchlevel, parse_branch_sha1, parse_default ]
	for parser in parsers:
		version, build_string_prefix = parser(raw_version, giturl)
		if version is not None:
			break

	# Heuristic for converting the (unnaturally) large LSST version numbers
	# to something more apropriate (i.e. 10.* -> 0.10.*, etc.).
	if re.match(r'^1[0-9]\.[0-9]+.*$', version):
		version = "0." + version

	# add plusver to version as .postNNN
	if plusver:
		version += ".post%d" % int(plusver)

	# remove any remaining '-'
	if '-' in version:
		version = version.replace('-', '_')

	# Make sure our version is conda-compatible
	try:
		from conda.resolve import normalized_version
		normalized_version(version)

		compliant = True
	except:
		compliant = False

	return version, build_string_prefix, buildnum, compliant

