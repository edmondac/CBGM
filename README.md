INTRODUCTION
------------
This is my implementation of the [CBGM](https://www.uni-muenster.de/INTF/Genealogical_method.html).
It was designed for testing and changing the various algorithms and is not (therefore) the fastest
user-facing package. The idea was that everything be calculated from scratch each time - although
in later development I added a Genealogical Coherence Cache for convenience (and speed). If you 
change the input data then remember to delete the old cache...

INSTALL
-------
1. You need these packages installed (these are the Ubuntu names):
 - openmpi-bin
 - libopenmpi-dev
 - graphviz
 - python3-dev
 - libgraphviz-dev
2. Then you can install using pip straight from github, like this:
 - pip install git+https://github.com/edmondac/CBGM
3. OR clone the repository and do one of the following:
 - python setup.py develop  # if you want to edit the code
 - python setup.py install  # if you just want to use it 

USE
---
The main program is cbgm.
Run `cbgm --help` for info, and for info about the subcommands do, for example,
`cbgm combanc --help`.

Similarly, see the help for the other programs. They all start 'cbgm_'.

DEVELOPER DOCUMENTATION
---
To create the code documentation, run `doxygen doxygen.conf`

TESTING
---
To run the unit tests, run `./test.sh` or just `python -m unittest discover CBGM`

Also see the "examples" folder, including the README.sh in there, which can be executed
with bash to test the common CBGM features.

REFERENCING
---
To reference this software, please use the DOI: [![DOI](https://zenodo.org/badge/78880568.svg)](https://zenodo.org/badge/latestdoi/78880568)


