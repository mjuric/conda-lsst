# Build Conda recipes for the LSST stack

## Overview

This repository contains the code to generate
[Conda](http://conda.pydata.org) recipes for LSST stack packages, and
scripts needed to build and upload them to http://anaconda.org

The recipes are generate using the information stored in
[EUPS](https://github.com/RobertLuptonTheGood/eups), the package manager
that LSST uses internally.

This code is alpha quality. It has been tested on OS X and Linux.

## Prerequisites

You need at least [Miniconda](conda.pydata.org/miniconda.html) with `conda-build`, `jinja2`, and `binstar` packages installed. For your convenience, there's a script in:
```bash
bash ./bin/bootstrap.sh
```
that will install all of these for you into a subdirectory named `miniconda`.

## Building Conda packages

To generate all packages and upload them to anaconda.org, run as follows:

```bash
# If on Linux, build patchelf v0.8
conda build recipes/static/patchelf

# Build the two prerequisites
(cd recipes/static/eups           && conda build . && binstar upload -u lsst $(conda build . --output) )
(cd recipes/static/legacy_configs && conda build . && binstar upload -u lsst $(conda build . --output) )

# Generate stack recipes (in recipes/generated subdirectory)
./bin/generate-conda-packages samples/b1488.txt sims_maf

# Build the packages from the recipes
bash recipes/generated/rebuild.sh

# Upload to anaconda.org
binstar login			# Run this once to log in with your anaconda.org credentials
bash recipes/generated/binstar-upload.sh
```

Build logs are stored in `recipes/generated/<packagename>/_build.log`.
Failed builds can be debugged by changing into the source directory (usually
.../conda-bld/work) and running `./_build.sh <eupspkg_verb>` where the verb
is typically `build`.

## Installing Conda packages

This is alpha-quality code; for now, it's probably safest to install LSST
conda packages into a separate [Conda
environment](http://conda.pydata.org/docs/using/envs.html):

```bash
conda create --name lsst ipython-notebook
source activate lsst
```
Then, you'll need to tell Conda about the LSST [anaconda.org](http://anaconda.org) channel:

```bash
conda config --add channels http://conda.anaconda.org/lsst/channel/dev
```

(note: this script currently publishes everything onto the 'development'
channel named `dev`, as you can tell from the URL above).

Then, to install (for example) `sims_maf`, run:

```bash
conda install lsst-sims-maf
```

## Running Conda-delivered LSST codes

Though delivered through Conda, the LSST codes are still managed by EUPS
under the hub.  You'll therefore need to set up the EUPS environment and the
individual packages being able to use them:

```bash
source eups-setups.sh	   # this activates EUPS (it's the equivalent of loadLSST.bash)
setup sims_maf           # the usual EUPS command to setup a product

#... run IPython notebooks, etc ...
```

(note: adjust the instructions above as appropriate for your shell).
