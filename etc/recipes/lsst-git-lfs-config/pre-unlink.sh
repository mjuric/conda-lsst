#!/bin/bash -e

# NOTE: if you change $CREDENTIALS_FILE, update post-link.sh with the new location
CREDENTIALS_FILE="$PREFIX/etc/git-lfs-lsst-anonymous-credentials"

# Make sure the new environment is on our path
export PATH="$PREFIX/bin:$PATH"

# Reverse the actions of pre-link
rm -f "$CREDENTIALS_FILE"

for HOST in $(cat "$PREFIX/etc/lsst-git-lfs-hosts.txt"); do
	git config --system --remove-section "credential.https://$HOST"
done

git config --system --unset "lfs.batch" false
