#!/bin/bash
#

PREFIX="$PREFIX/opt/lsst/$PKG_NAME"

# initialize EUPS
source eups-setups.sh

# copy to destination
mkdir -p "$PREFIX"
cp -a ups "$PREFIX"

# declare everything with a table file
for table in ups/*.table; do
	PRODUCT=$(basename $table .table)
	eups declare -t current -r "$PREFIX" "$PRODUCT" system 
done

# compile all .cfg files so they don't get picked up as new by conda when
# building other packages
$PYTHON -m py_compile "$PREFIX/ups"/*.cfg

eups list

# TODO: explicitly append SHA1 to pkginfo
# .........
