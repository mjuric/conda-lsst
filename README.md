# Package the [LSST Software Stack](http://dm.lsst.org) with [Conda](http://conda.pydata.org)

`conda-lsst` is a community-driven project created to make it easier for the
broader community to obtain and run the most excellent LSST codes
(disclaimer: the principal author of `conda-lsst` is also the LSST DM
Project Scientist; debias accordingly).

**IMPORTANT: `conda-lsst` is not a product of the [LSST project](http://lsst.org).** 
It is an independent (and highly experimental) effort. For all questions or
support, please open an issue in this repository or contact the authors.

## Overview

This repository contains the utility `conda-lsst` that can generate
[Conda](http://conda.pydata.org) recipes for LSST stack packages, build
them, and upload to a remote web server (or a hosted service such as
[anaconda.org](http://anaconda.org)) from where they will be installable
using `conda install`.

You *only* need this code if you wish to create and distribute your own build
of the LSST stack; `conda-lsst` is **not** needed to just use the LSST
codes. If all you want is to *install* the LSST stack, skip to the
[Installing](#installing-lsst-software-using-conda) section.

The recipes are generated using the information stored in
[EUPS](https://github.com/RobertLuptonTheGood/eups), the package manager
that LSST uses internally.

This code is beta quality; it is expected to work on OS X and Linux.

## Prerequisites

You need at least [Miniconda](conda.pydata.org/miniconda.html) with `conda-build`, `jinja2`, 
`binstar`, `requests`, `sqlalchemy` packages installed, and the `requests_file` python
module (install with `pip install requests_file`). For your convenience, there's a
script, [./bin/bootstrap.sh](bin/bootstrap.sh), that when run:
```bash
bash ./bin/bootstrap.sh
```
will install all of these for you into a subdirectory named `miniconda`.

## Building Conda packages

To generate all packages and upload them to a remote service, run someting like the following:

```bash
# Add conda-lsst to PATH. This will allow you to call it as `conda lsst`
export PATH="$PWD/bin:$PATH"

# If on Linux, build patchelf v0.8 (but see the note below)
conda build recipes/static/patchelf

# Build the prerequisites (but see the note below)
conda build recipes/static/eups
conda build recipes/static/legacy_configs

# Build conda packages for LSST codes (the recipes will be stored in recipes/generated subdirectory)
conda lsst build build:b1488 lsst_distrib lsst_sims

# Option #1: Upload to anaconda.org
binstar login			# Run this once to log in with your anaconda.org credentials
conda lsst upload --user lsst --channel dev	# replace user/channel with your credentials

# Option #2: Upload to a remote web server
conda lsst upload ssh lsst-dev.ncsa.illinois.edu public_html/conda/dev \
      --conda /path/to/bin/conda/on/the/remote/server
```

Note: If the packages for the recipes in the static directory (i.e., `eups`,
`legacy_configs` already exist on the upstream channel, there's no need to
build them again.  You generally need to build them only if you're
bootstrapping a new conda channel from scratch, or have updated their
versions.

`conda-lsst` is [smart about not rebuilding](#tracking-rebuilds) packages
that have already been built.

Build logs are stored in `recipes/generated/<packagename>/_build.log`.
Failed builds can be debugged by changing into the source directory (usually
.../conda-bld/work) and running `./_build.sh <eupspkg_verb>` where the verb
is typically `build`.

## Installing LSST software using Conda

The LSST stack builds are kept on http://eupsforge.net/conda/dev channel; you'll
need to tell `conda` about it:

```bash
conda config --add channels http://eupsforge.net/conda/dev
```

Then, to install (for example) `sims_maf`, run:

```bash
conda install lsst-sims-maf
```

The binaries are currently being built for 64 bit Linux (any variant newer
than RHEL 6) and OS X (10.9 or later). See [here](#binary-compatibility)
for more on binary compatibility.

## Running Conda-delivered LSST software

Though delivered through Conda, the LSST codes are still [managed by
EUPS](#package-management-eups-and-conda) under the hood.  You'll therefore
need to set up the EUPS environment and the individual packages being able
to use them:

```bash
source eups-setups.sh	   # this activates EUPS (it's the equivalent of loadLSST.bash)
setup sims_maf             # the usual EUPS command to setup a product

#... run IPython notebooks, etc ...
```

(note: adjust the instructions above as appropriate for your shell).

## Technical Details

### Package Management: EUPS and Conda

LSST code base consists of more than a hundred packages (largely written in
C++ and Python) that depend on each other at build and run time.  LSST
natively uses [EUPS](https://github.com/RobertLuptonTheGood/eups) as the
package manager (EUPS preferst the term *product*).  EUPS provides a way to
record dependencies (through so-called "table files", stored in the `ups/`
subdirectory of each package), as well as a uniform mechanism to build code
that the packages contain irrespective of their internal build system.  The
latter is known as `eupspkg` and is described in some detail in the
docstring of the
[eupspkg.py](https://github.com/RobertLuptonTheGood/eups/blob/master/python/eups/distrib/eupspkg.py)
EUPS module. EUPS also provides a facility to distribute code in source
form, but it does not have a facility do distribute binaries.

[Conda](http://conda.pydata.org) is a package manager written for the
Anaconda Python distribution.  It has support for building and distribution
of binaries: given a *recipe* -- a shell script that contains commands
needed to build the binary, plus some metadata -- the `conda-build` utility
will build the source and tarball it into a "conda package" (physically, a
`.tar.bz` file).  When uploaded to a [specially
formatted](http://conda.pydata.org/docs/spec.html#repository-structure-and-index)
web-accessible directory (or a hosted service such as anaconda.org), these
binary packages can then be installed by the user using the `conda install`
command.

The way we "marry" EUPS and Conda is by a) building EUPS itself as a Conda
package, and b) distributing pre-built EUPS products as Conda packages
themselves.  We therefore primarily utilize Conda as a convenient binary
packaging and distribution mechanism; the products themselves still need to
be `setup`-ed using the usual EUPS commands, but the `eups distrib install`
step (which would've built them from source) is now replaced by a simple
`conda install` (which simply unpacks the binary).  We also make EUPS itself
a dependency of all products: running `conda install lsst-distrib` will now
install both the LSST stack and EUPS itself (thus obviating the need for a
separate `newinstall.sh` script).

### The code: `conda-lsst` utility

The `conda-lsst` script uses the package dependency information extracted
from EUPS, and the eupspkg build system, to generate conda recipes that
build LSST codes **for a specific release**, build those recipes, and upload
the results to a package repository.

This section describes technical details and design consideration that went
into the code. The basic instructions on how to run it are above.

#### Overview: what happens when you run `conda lsst build`

 * `conda lsst build` reads the list of all products, their versions, and their
   dependencies from the manifest file (the first argument). The remaining
   arguments list the EUPS names of the products to be turned into conda
   packages.  Only "top level" products needs to be specified --
   `conda-lsst` will traverse the dependency tree and process all
   dependencies as necessary.

 * The list of products will be topologically sorted and a recipe
   will be created in `recipes/generated` subdirectory for each one that
   needs to be built.

 * All channels known to `conda build` (see the `channels` global
   variable) will be searched for packages with an identical recipe. If
   one is found, that means the package has already been built and doesn't
   need to be rebuilt once again (in which case a '.done' file will be
   placed into the particular product's recipe directory). N.b.: the actual
   lookup is sped up by hashing and using a database ([see
   below](#tracking-rebuilds)).
   
 * Unless `--dont-build` was given on the command line, `conda lsst build`
   will run `conda build` on each recipe, to build the packages. The results
   are stored in `$CONDA_ROOT/conda-bld/<platform>/` directory (where platform
   is typically `osx-64` or `linux-64`, depending on your machine).

 * The resulting packages can be uploaded to a remote repository using the
   `conda lsst upload` command. It knows how to upload to anaconda.org and
   via `ssh` to arbitrary servers.

#### Inputs

We don't use EUPS directly to extract the dependency information (though we
could!), but instead use the `manifest.txt` files generated by
[`lsstsw`](http://github.org/LSST/lsstsw) (the backend machinery for LSST's
CI system).

A `manifest.txt` file lists all products, EUPS versions, dependencies, and
git SHA1s for all products in a "build" (one run of buildbot).  Using a
`manifest.txt` file as input allows us to generate binary Conda packages for
any given build.

Subsets of the build can also be generated by providing a list of top-level
packages on the command line (e.g., very useful when debugging, as one
doesn't need to repeat a whole build for a quick test).

Given a buildbot build tag, one can pull the `manifest.txt` directly from
[versiondb directory](https://github.com/lsst/versiondb/tree/master/manifests)
where they are kept, e.g.:
```bash
conda lsst build build:b1497 wcslib
```

#### Conda-packaged EUPS

Conda-packaged EUPS, when unpacked by `conda install`, is placed into:
```
$ROOT/opt/eups/
```
and is configured to store its database (`ups_db`) information in
`$ROOT/var/opt/eups/`.  `$ROOT` above refers to the root of the Conda
environment you're installing into.

We've chosen **not** to install the EUPS binary (`eups`) into the global
`$ROOT/bin/` directory (that is on the users' path).  This is because EUPS
needs to be correctly initialized before use, and it's likely users would
forget to do this.  The initialization is typically done by `source`-ing the
`setups.sh` script from its `bin/` directory (this is the majority of what
`loadLSST.sh` does).  The conda package links those scripts into the global
`$ROOT/bin/` directory, but prefixed with `eups-`. Therefore, to initialize
EUPS, you need to run:
```bash
source eups-setups.sh
```
(or `.csh`, `.zsh`, etc., depending on your shell). Note that it's not
necessary to specify the full path to `eups-setups.sh` -- scripts to be
sourced are looked up on `$PATH`.

For details, see the recipe in [`recipes/static/eups`](recipes/static/eups).

Conda-packaged EUPS is **fully functional**. You can use it to install
additional EUPS products (for example, with `eups distrib install`), add
tags, etc.  We only recommend against using it to remove existing products
installed through `conda`.

#### Conda-packaged LSST products

The binaries produced by generated recipes unpack into:
```
$ROOT/opt/lsst/<product>/<version>/
```
directory, where `product` is the EUPS product name and the `version` is the
EUPS version (note: these can be different from the Conda names and
versions).

Their EUPS information (`.version` and `.chain` files) unpacks itself into
`$ROOT/var/opt/eups/ups_db`. Therefore, EUPS becomes aware of the new
product as soon as it's installed.

For details, see the section on [the build system](#the-build-system) and
the files in the [templates/](templates/) subdirectory.

#### EUPS tags

All packages come tagged with two EUPS tags: `current` and `conda`. As Conda
doesn't support having more than one version of a package installed in the
same environment, having everything tagged as current is the right thing to
do.

It should be easy to extend 'conda-lsst' to take arbitrary additional tags
-- all they do is generate extra `.chain` files. The only complication is
that all tags EUPS knows about must be declared in
`$ROOT/var/opt/eups/ups_db/global.tags` file; the code already automatically
handles that using a `pre-link.sh` script (see
`templates/pre-link.sh.template`).

Note that once the package is installed, you can use EUPS to declare
additional tags, as you wish.

#### The build system

`conda lsst build` generates the build recipes by filling out the missing
information in `.template` files found in the [templates/](templates/)
directory. The generation is completely automatic.

The build maximally reuses the `eupspkg.sh` build system that all LSST EUPS
packages use; in essence, the generated `build.sh` script does the
following:
```bash
source eups-setups.sh

eupspkg prep
eupspkg config
eupspkg build
eupspkg install

python -m compileall ...

eupspkg decl
eups declare -t <tags> <product> <version>
```
This is essentially the same sequence performed by EUPS when building
packages with `eups distrib install`.

All the added complexity here (compared to what you'd find in
[eupspkg.py](https://github.com/RobertLuptonTheGood/eups/blob/master/python/eups/distrib/eupspkg.py#L938))
comes from the need to handle various corner cases, relocateability, and to
inject correct build flags so as to make the binaries redistributable across
multiple versions of the operating system (e.g. 
`MACOSX_DEPLOYMENT_TARGET`).  Note: `build.sh.template` script also needs
some more work and cleaning up
-- it's likely possible to substantially simplify it!

This build script is executed by `conda build` to build and tarball the
binary package (with the metadata about the package such as the name,
version, and dependencies coming from `meta.yaml`, which is also generated
by filling out a template).

#### Overrides for packages supplied by Anaconda

Some products that are distributed with EUPS (either as full packages or
stubs) already exist in default Conda repositories.  Examples include
`numpy`, `swig`, `scons`, `twisted`, `protobuf`, etc.  We don't need to
create new recipes and build those packages.

However, because of the way the current
[`sconsUtils`](http://github.com/lsst/sconsUtils) build system works, those
packages still need to be declared to EUPS and their `.cfg` files need to be
present otherwise their dependencies won't know how to build themselves.

The solution to this problem has two parts:
 
 * Firsly, the `.table` and `.cfg` files of all such packages have been 
   collected in one [legacy_configs](http://github.com/mjuric/legacy_configs)
   repository. A conda package for this repository is built by a recipe in
   `recipes/static/legacy_configs`, and declares all the products in question
   to EUPS.

 * Second, the dependency on any of these packages is changed to a
   dependency on `legacy_configs`. Therefore, the package that (for example)
   requires `protobuf` will pull in `legacy_configs` when it's build with
   `conda build` or installed with `conda install`

Caveats:

 * the `.table` and `.cfg` files have been collected by hand; any time they
   change, the `legacy_configs` repository needs to be updated. A better way
   to do this would be to extract these files on the fly, from the content
   of the relevant commit of their individual parent product's git repos.
   
 * these products are listed by hand in the `internal_products` variable in
   `conda-lsst`. If the list changes, it needs to be updated by hand.

This is all a workaround; the long-term solution is not to depend on `.cfg`
files for builds and instead use something more standard, like `pkg-config`.

#### Skipped products

The code currently skips over a few (optional) products, most notably
`afw-data` (that is very large). This is hardcoded in the `skip_products` variable.

#### Patching

Any conda-specific patches needed to build the products should be placed in
`<patches>/<product>/` directory, with a `.patch` extension. They should
apply with `patch -p0`. See the patches currently there for examples.

Hint: if you're generating the patches with `git diff` (as you probably
should), use something like:
```
git diff --no-prefix master > mypatch.patch
```
to have the output at the `-p0` level.

Note: there is currently no way to declare a patch should only be applied
for certain commits (or commits coming before a certain commit).

#### PyPI dependencies (and missing/undeclared dependencies)

Some (external, wrapped) EUPS products, most notably `pyfits` and `pymssql`
are distutils packaged Python products that transparently use `easy_install`
to install additional dependencies. Conda does not allow this (and rightly
so, as it makes it impossible to guarantee offline installs).

`conda lsst build` automatically generates conda recipes and builds packages
for dependencies from PyPI. These are **not** prefixed with `lsst-`, like
other EUPS packages (see [Naming and Versioning](#naming-and-versioning)
below).

The information on which packages need this treatment is hardcoded in
`missing_deps` variable. Note that some EUPS packages have *undeclared*
dependencies as well (e.g., `sims_catalogs_generation` depends on
`sqlalchemy`).

#### Making packages relocatable

A conda package can be installed into any directory on the end-user's
system. It therefore needs to be relocatable.

Conda already has the mechanisms that greatly (and largely transparently)
help make this happen (see [the entry about relocatable
packages](http://conda.pydata.org/docs/building/meta-yaml.html#making-packages-relocatable)
in conda documentation).

This mechanism (among other things) ensures that our codes built against
libraries suppled by conda (those in `$ROOT/lib`) will be dynamically linked
against them at the end-user's system (this is typically acute for
`libssl.so`, where the system versions vary wildly compared to the Conda
ones).

That said, we did have to undertake two additional steps:

 * On OS X, we needed to inject the `-headerpad_max_install_names` option
   (e.g., see
   [here](http://blog.yimingliu.com/2008/01/23/building-dynamic-library-on-os-x/))
   to the linker command line for `install_name_tool` to work reliably.
   
 * On Linux, the version (v0.6) of [`patchelf`](https://github.com/NixOS/patchelf)
   supplied by Conda is buggy (it corrupts `afw.so`). We've had to upgrade
   to `patchelf` v0.8 to work around this. The conda recipe is in
   `recipes/static/patchelf`.

Note that we don't need (or want) the paths to *our* libraries to be
hardcoded into the libraries they depend on, as EUPS will handle this
through `LD_LIBRARY_PATH`. In fact, hardcoding it (e.g., in a
[RPATH](http://blog.tremily.us/posts/rpath/) entry) would make it impossible
to mix-and-match EUPS versions of different packages (for those inclined to
do so) as the `RPATH` entry takes precedence over `LD_LIBRARY_PATH`.

That said, it may be nice to encode the path to other libraries in
[`RUNPATH`](http://blog.tremily.us/posts/rpath/), to have a default fallback
when `LD_LIBRARY_PATH` is not set.

#### Binary compatibility

Binary compatibility is largely determined by the presence (or absence) on
the end-user's system of system libraries and frameworks that the code has
been built against.

On OS X, we build with `MACOSX_DEPLOYMENT_TARGET=10.9` set, which should
ensure that the built binaries work on OS X 10.9 (Mavericks) and later.
Older systems are unsupported because they utilise a different
implementation of the C++ standard library (`libstdc++` vs `libc++`).

On Linux, we build on a RHEL6-compatible system, with `gcc` 4.4 and `glibc`
2.12. Running on any newer distribution is expected to work.

#### Naming and Versioning

Conda follows different conventions and imposes additional restrictions on
package naming and version format:

 * Conda package names must be all lower case. They are allowed to contain
   the '-' sign, however.

 * Conda versions consist of three parts:

   * The version, preferably in  [PEP-386](https://www.python.org/dev/peps/pep-0386/)
     format. This is the "real" version of the package. '-' signs are not
     allowed in version strings. Letters are also undesirable (as they're
     interpreted -- see the PEP above).

   * The build number. This number should be incremented every time the
     *conda* recipe changes and a new binary is rebuilt (while the actual
     upstream source has not changed).

   * The build string. This is an arbitrary string that isn't used anywhere
     when comparing versions. It can be used to record some meaningful
     information about the build itself (e.g., the SHA1 of the source). By
     convention, the build string is usually of the form
     `<something>_<buildnumber>` or (in case there is no prefix), just
     `<buildnumber>`

For more details, see
[here](http://conda.pydata.org/docs/spec.html#package-match-specifications).

By convention, canonical Conda package names are written out as
`<package_name>-<version>-<buildstring>`.

Given those constraints, converting EUPS names+versions to Conda
names+versions is done as follows:

  * The EUPS product name is transformed to conda package name by replacing
    all the underscores '_' by dashes, '-'. The dashes as word separators
    seem to be a generally accepted convention in Conda world.
  * We also prepend an `lsst-` to it, except in cases where it would be
    silly (e.g., `lsst-lsst-distrib`).
  * Some products are given different names by fiat (see the
    `eups_to_conda_map` variable in the code).

Converting versions is tough -- for the exact heuristics see the code in
`eups_to_conda_version()` function in the code. That said, here's roughly
what happens:

  * Any versions of the form `X.Y.Z.W....` are left as is.
  * Any version that end in `xxx.lsstN` are converted to `xxx.N`
  * Any versions of the form of `xxx-N` are converted to `xxx.N`
  * If a version has a SHA1 embedded, it's moved or copied to the build
    string portion of the Conda version.
  * Any version of the form `X.Y.Z...` where `X` is between 10 and 20 is
    guessed to be an LSST package (as opposed to some external code that we
    distribute, for example `gsl`), and a 0 is prepended to it.  It is
    highly unusual in the Conda world to have version 10.x of something
    that's really alpha-quality code; this brings the version number to
    sometning more consistent with the state of the codebase.
  * Finally, the +N suffixes are converted to .000N suffixes (i.e.,
    formatted as `%04d`).
  * The conda build number always starts at zero, and is incremented every
    time the conda recipe used to build the source changes (see
    [below](#tracking-rebuilds)).

Some examples:
```
skypix-10.0+235             -->  skypix-0.10.0.0235_1
obs_test-10.1-4-g461b62d+49 -->  obs_test-0.10.1.4.0049-461b62d_1
boost-1.55.0.lsst1-2+3      -->  lsst-boost-1.55.0.1.2.0003-1
```

#### Tracking rebuilds

`conda lsst` does its best to avoid rebuilding code it has already built. 
It does this by comparing the generated recipe to the recipes of already
built packages (on channels that `conda lsst` knows about) that have the
same name and version (but not the build number or build string).  If the
recipes are the same (modulo build number/string; see below), the builds
would result in identical results and therefore no new build is necessary.

A *rebuild* is when the same source code (i.e., having the same git SHA),
including the dependencies and EUPS versions, is rebuilt using a different
recipe (e.g., the recipe may have been modified to change a compiler flag,
or add a new a conda-specific patch, etc.). This may happen when the
recipe templates in `templates/` are changed. A rebuild will keep the
same version, but the build number (and therefore the build string --
by convention, build strings are some `<prefix>_<buildnum>` or just
`<buildnum>`) will increment to reflect this is a rebuild (an example may be
lsst-boost-1.55.0.1.2.0003-0 and lsst-boost-1.55.0.1.2.0003-1).

While conceptually simple, this comparison of recipes would be extremely
inefficient if implemented naively: `conda lsst` would need to download
every built package, from every channel, extract the recipes, and compare
them to the recipe(s) of interest (modulo build number/string) until a match
is found. Since built packages are expected to grow to hundreds of GB, the
naive implementation is infeasible.

Instead, we cache the *hashes* of recipes (minus the lines in `meta.yaml`
that define the build number/string) in a local sqlite database (in
`pkginfo-cache/<platform>/cache-db.sqlite`). When a new recipe is generated,
it is hashed and compared to the hashes in the database.

`conda lsst` refreshes this cache every time it is run, unless
`--no-cache-refresh` option is given; if a new package is detected in any of
the channels, it's downloaded, the recipe hashed and cached.  Similarly, any
packages that are removed are purged from the cache.

This is truly a cache -- it is safe to delete; `conda lsst` will
transparently recover if it's not present.

#### Package repositories

To allow the user to use the binaries, they need to be uploaded to a
"channel" of a conda repository. This repository can either be on the
anaconda.org hosted service, or a HTTP-accessible directory on a remote
server to which you can SCP the files.

`conda lsst upload` gives you two options:

  * `conda lsst upload binstar` will upload to anaconda.org
  * `conda lsst upload ssh <server> <dir> [--conda]` will upload to a remote
    server using `ssh` and `scp` (or `rsync`).

For example, to upload packages to a repository in `~/public_html/conda/dev`
directory on `lsst-dev.ncsa.illinois.edu`, I use the following command:
```bash
conda lsst upload ssh lsst-dev.ncsa.illinois.edu public_html/conda/dev \
      --conda /ssd/mjuric/projects/lsst_packaging_conda/miniconda/bin/conda
```
where the `--conda` option specifies the full path to the `conda` binary on
the *remote* server. This directory is exposed to the web as
http://eupsforge.net/conda/dev; for a user to install from this channel,
they'd run:
```bash
conda config --add channels http://eupsforge.net/conda/dev
```
after which the usual `conda install` command will find the packages
available there.

Conda repositories follow a [simple package repository
format](http://conda.pydata.org/docs/spec.html#repository-structure-and-index).
That **they have to be initialized** before being used; for example:
```bash
cd path/to/my/channel
mkdir osx-64 linux-64
conda index osx-64
conda index linux-64
```
`conda index` will create the `repodata.json` (and `repodata.json.bz2`)
files that `conda` client uses to search for packages in the channel. `conda
lsst upload` automatically runs `conda index` after every upload.
