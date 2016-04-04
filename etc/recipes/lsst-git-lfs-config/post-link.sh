#!/bin/bash -ex

# NOTE: if you change $CREDENTIALS_FILE, update pre-unlink.sh with the new location
CREDENTIALS_FILE="$PREFIX/etc/git-lfs-lsst-anonymous-credentials"

# Make sure the new environment is on our path
export PATH="$PREFIX/bin:$PATH"

# Turn of git-lfs batch API (not supported by LSST's git-lfs servers)
git config --system --add "lfs.batch" false

# create the credentials cache, and point the credentials helper to the cache
# the cache has empty u/p, enabling anonymous access
mkdir -p "$PREFIX/etc"
rm -f "$CREDENTIALS_FILE"

for HOST in $(cat "$PREFIX/etc/lsst-git-lfs-hosts.txt"); do
	# Tell git to look for credentials for this host in $CREDENTIALS_FILE
	git config --system --add "credential.https://$HOST.helper" "store --file '$CREDENTIALS_FILE'"
	
	# Add a credential for anonymous access
	echo "https://:@"$HOST >> "$CREDENTIALS_FILE"
done
