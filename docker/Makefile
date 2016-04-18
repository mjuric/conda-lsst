#
# Build the docker container image apropriate to this account
#

image:
	@ docker build -t centos5-host --build-arg GROUP_ID=$$(id -g) --build-arg USER_ID=$$(id -u) --build-arg GROUP_NAME=$$(id -g -n) --build-arg USER_NAME=$$(id -u -n) --build-arg HOME=$$HOME .
	@ echo
	@ echo '###################################################################################################################'
	@ echo Add this to your .bashrc to have rebuild.sh invoke itself in the container context:
	@ echo
	@ echo '    export REBUILD_RECIPES_IN_CONTAINER="docker run --rm -it -v $$HOME:$$HOME --hostname conda-centos5 centos5-host"'
	@ echo
