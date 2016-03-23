#!/bin/sh

# Install script, modified from the bundled install.sh
# and changed so that it doesn't call 'git lfs install'
# automatically (thus polluting the ~/.gitconfig of the
# user building the package.
#
# git-lfs (de)initialization is now done pre-(un)link
# scripts

mkdir -p "$PREFIX/bin"

rm -rf "$PREFIX"/bin/git-lfs*
for g in git*; do
	install $g "$PREFIX/bin/$g"
done
