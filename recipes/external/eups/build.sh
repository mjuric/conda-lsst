#!/bin/bash
#
# This recipe:
#
# - Installs EUPS into $PREFIX/opt/eups,
# - Symlinks the EUPS setup scripts into $PREFIX/bin, as eups-setups.{sh,zsh,csh,...},
# - Points the default EUPS_PATH to $PREFIX/var/opt/eups
#
# To use it, the user should source one of the eups-setups.XX scripts.
#

mkdir -p $PREFIX

#
# configure & build
#
./configure --prefix="$PREFIX/opt/eups" --with-eups="$PREFIX/var/opt/eups" --with-python="$PYTHON"
make

#
# install
#
make install
chmod -R u+w "$PREFIX/opt/eups"
echo "Database of EUPS-built products" > "$PREFIX/var/opt/eups/ups_db/README"

#
# Link only the setup scripts into bin
#
for script in "$PREFIX/opt/eups/bin"/setups.*; do
	name=$(basename $script)
	ln -s "$script" "$PREFIX/bin/eups-$name"
done

#
# Generate a helper/reminder script, so when the user runs 'eups' they're
# pointed to sourcing the right scripts..
#

cat > "$PREFIX/bin/eups" <<-EOT
	#!/bin/bash
	#
	# Helper script to point the user to source the right setups script to start
	# EUPS.
	#

	if [[ -x "\$EUPS_DIR/bin/eups" ]]; then
		exec "\$EUPS_DIR/bin/eups" "\$@"
	fi

	echo "To begin using EUPS, please source one of the following files, depending"
	echo "on the shell you're using:"
	echo
	echo "   source '$PREFIX/bin/eups-setups.sh'   # for sh/bash/ksh"
	echo "   source '$PREFIX/bin/eups-setups.csh'  # for csh/tcsh"
	echo "   source '$PREFIX/bin/eups-setups.zsh'  # for zsh"
	echo
	echo "After that, all the usual EUPS commands will work (e.g., eups, setup)."

	exit -1
EOT
chmod +x "$PREFIX/bin/eups"

ln -s "$PREFIX/bin/eups" "$PREFIX/bin/setup"
