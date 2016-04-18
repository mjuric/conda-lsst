FROM    centos:centos5

# Following instructions on:
# https://www.digitalocean.com/community/tutorials/docker-explained-using-dockerfiles-to-automate-building-of-images

# Get toolchain prerequisites
RUN	yum install -y \
		curl git \
		make glibc-headers glibc-devel patch bzip2 libgfortran bzip2-devel \
		flex bison which ncurses-devel zlib-devel which \
		libXext libSM libXrender \
		readline-devel

# fftw's eupspkg.cfg.sh gratuitously requires rsync
RUN	yum install -y rsync

# Install joe for mjuric
RUN	rpm -ivh http://dl.fedoraproject.org/pub/epel/epel-release-latest-5.noarch.rpm && \
	yum install -y joe

# Create user corresponding to our local user
ARG	GROUP_ID
ARG	GROUP_NAME
ARG	USER_ID
ARG	USER_NAME
ARG	HOME

RUN	groupadd -g $GROUP_ID $GROUP_NAME
RUN	useradd -d $HOME -g $GROUP_NAME -u $USER_ID $USER_NAME

ENV	PATH=$HOME/conda-lsst/miniconda/bin:$PATH

USER	$USER_ID
WORKDIR	$HOME
