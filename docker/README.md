# Build a CentOS 5 docker container to build conda LSST binaries

The `Dockerfile` in this directory will build a CentOS 5 docker container
with all `yum`-installed system dependencies required to build the LSST stack
with `conda`.

## Image

To build the image, run `make`. The `Makefile` will generate a Docker image
named `centos5-host`, that can be used to create a container to do builds
within the CentOS 5 OS context.

## Building

The `rebuild.sh` file that `conda lsst make-recipes` generates has hooks to
re-execute itself from within a container. Assuming the variable:

```
export REBUILD_RECIPES_IN_CONTAINER="docker run --rm -it -v $HOME:$HOME --hostname conda-centos5 centos5-host"
```

is defined, running `bash rebuild.sh` will re-run it from within the
container. It's best to add this to your `.bashrc`, so that every invocation
of rebuild ends up being run from within the container.

## Other tips (development)

The docker image we build has the `USER` changed to the current user, and
`WORKDIR` set to their current directory. If you ever need to run in the
root context, start the container and then do:

```
docker exec -u 0 -it <container_id> bash
```
