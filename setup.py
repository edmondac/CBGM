from setuptools import setup

setup(
    name='CBGM',
    version='2.2',
    packages=['CBGM'],
    url='https://github.com/edmondac/CBGM',
    license='MIT',
    author='Andrew Edmondson',
    author_email='ed@rameus.org.uk',
    description='Ed\'s implementation of the Coherence-Based Genealogical Method',
    scripts=[
        'bin/{}'.format(x) for x in ['cbgm_check_consistency',
                                     'cbgm_populate_db',
                                     'cbgm_apparatus',
                                     'cbgm_hypotheses_on_unclear',
                                     'cbgm_stripes',
                                     'cbgm']
    ],
    install_requires=[
        'coverage',
        'decorator',
        'graphviz',
        'mpi4py',
        'networkx==1.10',
        'pkg-resources',
        'pydot',
        'pygraphviz',
        'Pympler',
        'pyparsing',
        'toposort',
    ]
)
