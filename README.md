# Build Conda recipes for the LSST stack

## Overview

This repository contains the utility `conda-lsst` that can generate
[Conda](http://conda.pydata.org) recipes for LSST stack packages, build
them, and upload to a remote web server (or a hosted service such as
[anaconda.org](http://anaconda.org)) from where they will be installable
using `conda install`.

The recipes are generated using the information stored in
[EUPS](https://github.com/RobertLuptonTheGood/eups), the package manager
that LSST uses internally.

You *only* need this code if you wish to create and distribute your own build
of the LSST stack; `conda-lsst` is **not** needed to just use the LSST
codes.

This code is beta quality; it is expected to work on OS X and Linux.

## Prerequisites

You need at least [Miniconda](conda.pydata.org/miniconda.html) with `conda-build`, `jinja2`, 
`binstar`, `requests`, `sqlalchemy` packages installed, and the `requests_file` python
module (install with `pip install requests_file`). For your convenience, there's a script in:
```bash
bash ./bin/bootstrap.sh
```
that will install all of these for you into a subdirectory named `miniconda`.

## Building Conda packages

To generate all packages and upload them to a remote service, run someting like the following:

```bash
# Add conda-lsst to PATH
export PATH="$PWD/bin:$PATH"

# If on Linux, build patchelf v0.8
conda build recipes/static/patchelf

# Build the two prerequisites
(cd recipes/static/eups           && conda build . && binstar upload -u lsst $(conda build . --output) )
(cd recipes/static/legacy_configs && conda build . && binstar upload -u lsst $(conda build . --output) )

# Build conda packages for LSST codes (the recipes will be stored in recipes/generated subdirectory)
conda lsst build samples/b1488.txt sims_maf

# Option #1: Upload to anaconda.org
binstar login			# Run this once to log in with your anaconda.org credentials
conda lsst upload --user lsst --channel dev	# replace user/channel with your credentials

# Option #2: Upload to a remote web server
conda lsst upload ssh localhost public_html/conda/dev --conda /path/to/bin/conda/on/the/remote/server
```

`conda-lsst` is smart about not rebuilding packages that have already been
built.

Build logs are stored in `recipes/generated/<packagename>/_build.log`.
Failed builds can be debugged by changing into the source directory (usually
.../conda-bld/work) and running `./_build.sh <eupspkg_verb>` where the verb
is typically `build`.

## Installing LSST codes using Conda

As this is beta-qality code, it's recommended to install LSST
conda packages into a separate [Conda
environment](http://conda.pydata.org/docs/using/envs.html):

```bash
conda create --name lsst ipython-notebook
source activate lsst
```
The LSST stack builds are kept on http://eupsforge.net/conda/dev channel; you'll
need to tell `conda` about it:

```bash
conda config --add channels http://eupsforge.net/conda/dev
```

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
