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
