#
# Quick script to bootstrap a clean build environment
# MUST be run from the root package directory
#

set -e

if hash conda 2>/dev/null; then
	echo 'Detected existing conda on $PATH:'
	echo
	echo "    $(which conda)"
	echo
	echo 'Having multiple Conda installs on the path is not recommended.'
	echo 'Remove it and try again.'
	exit -1
fi

#
# Install Miniconda
#

if [[ ! -f "$PWD/miniconda/.installed" ]]; then
	# FIXME: Make this cross-platform
	rm -f Miniconda-latest-MacOSX-x86_64.sh
	rm -rf "$PWD/miniconda"
	wget https://repo.continuum.io/miniconda/Miniconda-latest-MacOSX-x86_64.sh
	bash Miniconda-latest-MacOSX-x86_64.sh -b -p "$PWD/miniconda"
	rm -f Miniconda-latest-MacOSX-x86_64.sh

	#
	# Install conda-build, jinja2
	#
	export PATH="$PWD/miniconda/bin:$PATH"
	conda install conda-build jinja2 binstar --yes

	# marker that we're done
	touch "$PWD/miniconda/.installed"
else
	echo
	echo "Found Miniconda in $PWD/miniconda; skipping Miniconda install."
	echo
fi


echo "Miniconda has been installed in $PWD/miniconda. Add it to your path:"
echo
echo "  export PATH=\"$PWD/miniconda/bin:\$PATH\""
echo
echo "and continue."
