INTRODUCTION
------------
This is my implementation of the CBGM. It was designed for testing and changing the 
various algorithms and is not (therefore) the fastest user-facing package. The idea
was that everything be calculated from scratch each time - although in later development
I added a Genealogical Coherence Cache for convenience (and speed). If you change the
input data then remember to delete the old cache...

INSTALL
-------
1) You need these packages installed (these are the Ubuntu names):
 - openmpi-bin
 - libopenmpi-dev
 - graphviz
 - python3-dev
 - libgraphviz-dev
2) You need a python 3.5 virtualenv, using the provided requirements.txt

USE
---
The main program is ./bin/cbgm.
Run `./bin/cbgm --help` for info, and for info about the subcommands do, for example,
`./bin/cbgm combanc --help`.

Similarly, see the help for the other programs in bin.

DOCUMENTATION
---
To create the code documentation, run `doxygen doxygen.conf`

TESTING
---
To run the unit tests, run `./test.sh`

Also see the "examples" folder, including the README.sh in there, which can be executed
with bash to execute the common CBGM features.
