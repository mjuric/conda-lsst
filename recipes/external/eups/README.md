To build, run:

    env GITREV=<git sha, tag, or branch> conda build .

To convert to other platforms, run:

    conda convert --platform=all <output_of_above.tar.bz2>

or

    conda convert --platform=all $(conda build . --output) --output pkgs

which will populate the subdirectory 'pkgs' with the result.

To upload to anaconda.org:

   binstar upload --force pkgs/*/*.bz2

.
