from setuptools import setup

setup(
    name='CBGM',
    version='1.14',
    packages=['', 'lib', 'example'],
    url='https://github.com/edmondac/CBGM',
    license='MIT',
    author='Andrew Edmondson',
    author_email='ed@rameus.org.uk',
    description='Ed\'s implmenetation of the Coherence-Based Genealogical Method',
    scripts=[
        'bin/cbgm',
        'bin/populate_db',
        'bin/apparatus'],
    package_data={'example': ['example/*']},
    install_requires=[
        'coverage',
        'decorator',
        'graphviz',
        'mpi4py',
        'networkx',
        'pkg-resources',
        'pydot',
        'pygraphviz',
        'Pympler',
        'pyparsing',
        'toposort',
    ]
)
