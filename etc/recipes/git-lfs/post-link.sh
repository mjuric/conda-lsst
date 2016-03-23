#!/bin/bash

# Make sure the new environment is on our path
export PATH="$PREFIX/bin:$PATH"

#
# Now add the filters to the *system* gitconfig file
#
git config --system --add "filter.lfs.clean" "git-lfs clean %f"
git config --system --add "filter.lfs.smudge" "git-lfs smudge %f"
git config --system --add "filter.lfs.required" "true"
