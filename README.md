# Build Conda recipes for the LSST stack

## Overview

This repository contains the code to generate
[Conda](http://conda.pydata.org) recipes for LSST stack packages, and
scripts needed to build and upload them to http://anaconda.org

The recipes are generate using the information stored in
[EUPS](https://github.com/RobertLuptonTheGood/eups), the package manager
that LSST uses internally.

This code is alpha quality, and has only been tested on OS X.

## Prerequisites

You need at least [Miniconda](conda.pydata.org/miniconda.html) with `conda-build` and `jinja2` packages installed. For your convenience, there's a script in:
```bash
bash ./bin/bootstrap.sh
```
that will install all of these for you into a subdirectory named `miniconda`.

## Building Conda packages

To generate all packages and upload them to anaconda.org, run as follows:

```bash
# Build the two prerequisites
(cd recipes/static/eups           && conda build . && binstar upload $(conda build . --output) )
(cd recipes/static/legacy_configs && conda build . && binstar upload $(conda build . --output) )

# Generate stack recipes (in recipes/generated subdirectory)
./bin/generate-conda-packages samples/b1467.txt sims_maf

# Build the packages from the recipes
bash recipes/generated/rebuild.sh

# Upload to anaconda.org
binstar login			# Run this once to log in with your anaconda.org credentials
bash recipes/generated/binstar-upload.sh
```

## Installing conda packages

You'll need to add the LSST anaconda.org channel first:

```bash
conda config --add channels http://conda.anaconda.org/lsst
```

Then, to install (for example) `sims_maf`, run:

```bash
conda install lsst-sims-maf
```

To use it, run:
```bash
source eups-setups.sh	# this activates EUPS
setup sims_maf

#... run IPython notebooks, etc ...
```
