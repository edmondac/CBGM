#!/usr/bin/env python
"""
Create a subset of a global stemma, with a list of witnesses and their immediate relations.
"""

COLOUR = '''[color="#b43f3f",
             fillcolor="#FF8A8A",
             style=filled]'''


def subset(glob_stem, output, witnesses, highlight):
    """
    Make a new dotfile
    """
    print("Reading %s and looking for any lines containing %s" % (glob_stem, witnesses))
    wits_s = set(witnesses)
    lines = ["strict digraph G {"]
    with open(glob_stem) as f:
        for line in f.readlines():
            # Get a list where all witnesses will be entries in their own right
            bits = set(line.replace('"', '').replace(';', '').split())
            if wits_s & bits:
                if len(bits) == 1:
                    # node line
                    line = '{} {};\n'.format(line.rstrip()[:-1], COLOUR)
                lines.append(line)

    lines.append('}')

    with open(output, 'w') as o:
        o.write(''.join(lines))

    print("Written %s" % output)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('global_stemma', help='DOT file representing the global stemma')
    parser.add_argument('output_file', help='Output filename for the subset DOT file')
    parser.add_argument('include_witness', help='Witness name', nargs='+')
    parser.add_argument('--highlight', help='Highlight the included witnesses', action='store_true')
    args = parser.parse_args()

    subset(args.global_stemma, args.output_file, args.include_witness, args.highlight)
