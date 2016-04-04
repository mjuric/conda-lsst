#!/bin/bash

# Make sure the new environment is on our path
export PATH="$PREFIX/bin:$PATH"

#
# Remove git-lfs configs from the *system* .gitconfig file
#
git config --system --remove-section "filter.lfs"
