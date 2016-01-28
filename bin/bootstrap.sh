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
	case "$OSTYPE" in
		linux*)  MINICONDA_SH=Miniconda-latest-Linux-x86_64.sh ;;
		darwin*) MINICONDA_SH=Miniconda-latest-MacOSX-x86_64.sh ;;
		*)       echo "Unsupported OS $OSTYPE. Exiting."; exit -1 ;;
	esac

	rm -f "$MINICONDA_SH"
	rm -rf "$PWD/miniconda"
	curl -O https://repo.continuum.io/miniconda/"$MINICONDA_SH"
	bash "$MINICONDA_SH" -b -p "$PWD/miniconda"
	rm -f "$MINICONDA_SH"

	#
	# Install prerequisites
	#
	export PATH="$PWD/miniconda/bin:$PATH"
	conda install conda-build jinja2 requests sqlalchemy pip --yes

	pip install requests_file

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
