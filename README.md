# [Conda](http://conda.pydata.org) recipe generator for the [LSST Software Stack](http://dm.lsst.org)

## Overview

This repository contains `conda-lsst`, a utility that generates
[Conda](http://conda.pydata.org) recipes for LSST stack packages. The
recipes are generated using the information stored in
[EUPS](https://github.com/RobertLuptonTheGood/eups), the package manager
that LSST uses internally.

`conda-lsst` also provides a convenient mechanism to build the generated
recipes in proper order, and to upload the resulting binaries to a remote
web server from where they will be installable using `conda install`.

You *only* need this code if you wish to create and distribute your own build
of the LSST stack; `conda-lsst` is **not** needed to just use the LSST
codes. If all you want is to *install* the LSST stack, skip to the
[Installing](#installing-lsst-software-using-conda) section.

This code is beta quality; it is expected to work on OS X and Linux.

## Prerequisites

You need at least [Miniconda](conda.pydata.org/miniconda.html) with
`conda-build`, `jinja2`, `requests`, and `sqlalchemy` packages installed, 
as well as the `requests_file` python module (install
with `pip install requests_file`). You will also need to build and
install the `git-lfs` and `lsst-git-lfs-config` conda packages using
the recipes found in `etc/recipes` directory. For your convenience,
there's a script, [./bin/bootstrap.sh](bin/bootstrap.sh), that when run:
```bash
bash ./bin/bootstrap.sh
```
will install all of these for you. Miniconda will be installed into a
subdirectory named `miniconda`.

### Docker containerized builds (Linux)

If you have docker, and want `conda` package builds to happein within a
CentOS 5 docker container (recommended, for maximum binary compatibility),
run:
```
cd docker
make
```
to create the necessary docker image.

Once `make` is run, it will print out the instructions on how to set
the `REBUILD_RECIPES_IN_CONTAINER` environmental variable and make the new
container known to `rebuild.sh`.

The `rebuild.sh` script that `conda lsst make-recipes` checks for the contents
of `$REBUILD_RECIPES_IN_CONTAINED` variable and uses it as a driver for `conda build`
(if present). It's best to export this variable from your `.bashrc`.

## Generating Conda recipes, and building the packages

To generate all packages and upload them to a remote service, run someting like the following:

```bash
# Add conda-lsst to PATH. This will allow you to call it as `conda lsst`
export PATH="$PWD/bin:$PATH"

# Tell conda where the channel we'll be uploading to is
conda config --add channels http://eupsforge.net/conda/dev

# Build conda packages for LSST codes (the recipes will be stored in the `recipes` subdirectory)
conda lsst make-recipes build:b1852 lsst_distrib lsst_sims --build

# Upload to the 'dev' channel
conda lsst upload
```

Note: `conda-lsst` is [smart about not rebuilding](#tracking-rebuilds) packages
that have already been built.

Build logs are stored in `recipes/<packagename>/_build.log`.
Failed builds can be debugged by changing into the source directory (usually
.../conda-bld/work) and running `./_build.sh <eupspkg_verb>` where the verb
is typically `build`.

The first parameter passed to `conda lsst make-recipes` is an [`lsst-build`
generated manifest](https://github.com/lsst/lsst_build). You may be familar
with these as `manifest.txt` files that `lsstsw` generates in its `build` 
directory. For "official" builds, they're also stored in the 
[canonical versiondb](https://github.com/lsst/versiondb/tree/master/manifests)
by the lsstsw's `rebuild` script when run on `lsst-dev` as `lsstsw`.

To find out which build manifests (as stored in the [canonical versiondb](https://github.com/lsst/versiondb) 
contain a particular product, use the `what-builds` utility. For example:
```
$ what-builds lsst_apps | tail
lsst_apps b2005
lsst_apps b2007
lsst_apps b2010
lsst_apps b2012
lsst_apps b2014
lsst_apps b2015
lsst_apps b2017
lsst_apps b2018
lsst_apps b2020
lsst_apps b2021
```

## Installing and Running Conda-delivered LSST softwre

See [this gist](https://gist.github.com/mjuric/1e097f2781bc503954c6) or the
[video tutorial](https://youtu.be/bxfG8PoVCLU).

The binaries are currently being built for 64 bit Linux (any variant newer
than RHEL 6) and OS X (10.9 or later). See [here](#binary-compatibility)
for more on binary compatibility.

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
`.tar.bz2` file).  When uploaded to a [specially
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
build LSST codes **for a specific release**. It also generates a script
to build those recipes (in dependency-sorted order), as well as provies
a convenient `upload` utility to upload the built binaries to a package
repository.

This section describes technical details and design consideration that went
into the code. The basic instructions on how to run it are above.

#### Overview: what happens when you run `conda lsst build`

 * `conda lsst make-recipes` reads the list of all products, their versions,
   and their dependencies from the manifest file (the first argument).  The
   remaining arguments list the EUPS names of the products to be turned into
   conda packages.  Only "top level" products needs to be specified --
   `conda-lsst` will traverse the dependency tree and process all
   dependencies as necessary.

 * The list of products will be topologically sorted and a recipe
   will be created in `recipes` subdirectory for each one that
   needs to be built.

 * Of all channels known to `conda build`, those matching `our_channel_regex`
   in `config.yaml` will be searched for packages with an identical recipe. If
   one is found, that means the package has already been built and doesn't
   need to be rebuilt once again (in which case a '.done' file will be
   placed into the particular product's recipe directory). N.b.: the actual
   lookup is sped up by hashing and using a database ([see
   below](#tracking-rebuilds)).
   
 * If `--build` is given on the command line, `conda lsst make-recipes`
   will run `conda build` on each recipe, to build the packages. The results
   are stored in `$CONDA_ROOT/conda-bld/<platform>/` directory (where platform
   is typically `osx-64` or `linux-64`, depending on your machine).

 * The resulting packages can be uploaded to a remote repository using the
   `conda lsst upload` command. It uses either `scp` or `rsync` to upload the
   results to the destination server.

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

For convenience, given a build tag, one can pull the `manifest.txt` directly from
[versiondb directory](https://github.com/lsst/versiondb/tree/master/manifests)
where they are kept. That lets you do things such as:
```bash
conda lsst make-recipes build:b1497 wcslib
```

#### Tuning the recipe generation: config.yaml and ~/.condalsstrc

Recipe generation is controlled by entries in [`config.yaml`](config.yaml) file.
They control virtually all aspects of recipe generation, from injecting
missing system dependencies, to defining the output directories and
default destination servers to upload to. Refer to comments in [`config.yaml`](config.yaml) for more.

##### Local overrides: ~/.condalsstrc

The settings from `condig.yaml` can be overridden by keys in `~/condalsstrc`. For
example, here's what I (mjuric) have in my `~/condalsstrc`:
```
$ cat ~/.condalsstrc
our_channel_regex: '^(?:https?://conda.lsst.mjuric.org/)(.+?)/?$'

upload:
  server:    'centos@conda.lsst.mjuric.org'
  dir_base:  '/var/www/html'
  conda:     'conda'
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
forget to do this. Instead, we install a dummy `eups` and `setup` scripts
there that remind the users of the need to initialize EUPS before continuing.

The initialization is typically done by `source`-ing the
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

For details, see the recipe in [`etc/recipes/eups`](etc/recipes/eups).

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
the files in the [`etc/templates`](etc/templates) subdirectory.

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
`etc/templates/pre-link.sh.template`).

Note that once the package is installed, you can use EUPS to declare
additional tags, as you wish.

#### How the generated recipes build the binaries

`conda lsst make-recipes` generates the build recipes by filling out the missing
information in `.template` files found in the [`etc/templates`](etc/templates)
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
`numpy`, `swig`, `scons`, `twisted`, etc.  We don't want to unnecessarily
duplicate functionality by building our own versions.

However, we can't just skip these. Because of the way the current
[`sconsUtils`](http://github.com/lsst/sconsUtils) build system works, those
packages still need to be declared to EUPS and their `.cfg` files need to be
present. Otherwise their dependents won't know how to build themselves.

The solution to this problem is not to perform the full build of packages
that Conda can supply to us, but to only copy the contents of their `ups/`
directories and declare them to EUPS.  To make it clear these are packages
that only carry the EUPS config files, we name them
`lsst-PRODUCTNAME-eups-configs`.  Secondly, whenever a product depends on
one of these packages, we inject the dependency on both the conda package,
as well as the relevant `-eups-configs` package.  For example, the `afw`
EUPS product depends on `numpy` and therefore the conda package `lsst-afw`
will depend on `lsst-numpy-eups-configs` and `numpy`.

The products to be considered internal (provided by conda) should be listed
by hand in the `internal_products` variable in `config.yaml`.

Note that this is really a workaround; the long-term solution is not to
depend on `.cfg` files for builds and instead use something more standard,
like `pkg-config`, as well as make it possible to run conda binaries w/o
EUPS.

#### Skipped products

The code currently skips over a few (optional) products, most notably
`afw-data` (that is very large). This is defined in the `skip_products`
variable in `config.yaml`

#### Patching

Any conda-specific patches needed to build the products should be placed in
`etc/patches/<product>/` directory (the location can be changed by
setting `patchdir` in `config.yaml`), with a `.patch` extension. They should
apply with `patch -p0`. See the patches currently there for examples.

Hint: if you're generating the patches with `git diff` (as you probably
should), use something like:
```
git diff --no-prefix master > mypatch.patch
```
to have the output at the `-p0` level.

We recommend to maintain conda-lsst patches on branches in the package's
repository (e.g. a `conda-patches` branch). To make it easy to create a
patch from a brancg in a git repo, use the `make-patch` utility as:
```
make-patch patch-name.patch master conda-patches
```
This creates a file `patch-name.patch` with a diff between
`master..conda-patches` in the `etc/patches/<product>/` directory, where
`<product>` is automatically inferred from the name of the `.table` file in
the git repo's `ups/` directory. If you omit the third argument to
`make-patch`, `HEAD` is assumed. If you omit the second argument, `master`
is assumed. Therefore, assuming you're on `conda-patches` branch, running:
```
make-patch patch-name.patch
```
is equivalent to the invocation above.

Note: there is currently no way to declare a patch should only be applied
for certain commits (or commits coming before a certain commit).

#### PyPI dependencies (and missing/undeclared dependencies)

Some (external, wrapped) EUPS products, most notably `sncosmo` and `pymssql`
are distutils packaged Python products that transparently use `easy_install`
to install additional dependencies. Conda does not allow this (and rightly
so, as it makes it impossible to guarantee offline installs).

For these packages to build, we need to:

  * manually create recipes for all of their dependencies, and place them in
    `etc/recipes`. The easiest way to do this is by using
    [`conda skeleton`](http://conda.pydata.org/docs/commands/build/conda-skeleton.html).
  * Declare their depenencies in `config.yaml` by adding them to the
    `dependencies` list, with their name prefixes by `recipe/`.

Here is an example of the entry for `pymssql`:
```
dependencies:
  pymssql:
    run:   [ cython, recipe/setuptools-git ]
    build: [ cython, recipe/setuptools-git ]
```

Note that some EUPS packages have *undeclared* dependencies on conda
packages as well (e.g., `pymssql` above depends on `cython`).

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

That said, we did have to undertake one additional step. On OS X, we needed
to inject the `-headerpad_max_install_names` option (e.g., see
[here](http://blog.yimingliu.com/2008/01/23/building-dynamic-library-on-os-x/))
to the linker command line for `install_name_tool` to work reliably.

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

On Linux, we build on a RHEL5-compatible system. Running on any newer
distribution is expected to work.

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
    `eups_to_conda_map` variable in `config.yaml`).

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

#### Tracking built recipes

`conda lsst` does its best to tell you which recipes have already been
built, so that you don't have to rebuild them (such recipes have a
.done file added to their directory, which the generated `rebuild.sh`
script reads and honors).

It does this by comparing the generated recipe to the recipes of already
built packages (on channels that match the `our_channel_regex` pattern
from `config.yaml`), that have the
same name and version (but not the build number or build string).  If the
recipes are the same (modulo build number/string; see below), the builds
would result in identical results and therefore no new build is necessary.

A *rebuild* is when the same source code (i.e., having the same git SHA),
including the dependencies and EUPS versions, is rebuilt using a different
recipe (e.g., the recipe may have been modified to change a compiler flag,
or add a new a conda-specific patch, etc.). This may happen when the
recipe templates in `etc/templates` are changed. A rebuild will keep the
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

`conda lsst upload` makes it easy to upload to the latter of the two. The
defaults in `config.yaml` are set up so that just running `conda lsst upload` 
will upload to a subdirectory of `~mjuric/public_html/conda` at
`lsst-dev.ncsa.illinois.edu`.

For example, assuming I have `http://eupsforge.net/conda/dev` in my
`~/.condarc`, running:
```
conda lsst upload
```
will upload the built packages to
`lsst-dev.ncsa.illinois.edu:~mjuric/public_html/conda/dev`. Note that to do
this, you need to have permissions to write to this directory.

This directory is exposed to the web as http://eupsforge.net/conda/dev; 
for a user to install from this channel, they'd run:
```bash
conda config --add channels http://eupsforge.net/conda/dev
```
after which the usual `conda install` command will find the packages
available there.

More options are available; see `conda lsst upload -h` for a more complete
summary.

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
