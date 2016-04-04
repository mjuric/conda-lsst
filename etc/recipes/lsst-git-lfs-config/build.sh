#!/bin/bash -e

#
# Copy the list of LSST's LFS hosts to a well known location.
# This file will be used by link/unlink scripts to add the proper
# lines to the system gitconfig file (and generate the credentials
# file).
#

mkdir -p "$PREFIX/etc"
cp lfs-hosts.txt "$PREFIX/etc/lsst-git-lfs-hosts.txt"
