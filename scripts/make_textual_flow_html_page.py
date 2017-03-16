#!/usr/bin/env python

"""
Script to create an HTML summary of the files created when running "cbgm -T ...". The folder structure
is expected to look like:
folder
 |
 |-c5
 |-c10
 |-cXX
 .
 .
 .
 |_c499

Each cXXX folder will contain many .svg files, and they should all contain equivalent listings.
"""


import string
import sys
import os
import shutil
import re


HERE = os.path.dirname(os.path.abspath(__file__))


JQUERY = "jquery-3.1.1.min.js"


HTML_TEMPLATE = """<html>
    <head>
        <title>$title</title>
        <script src="$jquery"></script>
        <style>
            div#listing {
                min-width: 10%;
                border-right: 1px dashed grey;
                height: 100%;
                overflow: auto;
                }
            div#images {
                min-width: 70%;
                float: right;
                margin-left: 10px;
                height: 100%;
                overflow: auto;
                }
            div#image {
                display: none;
            }
            div.showhideimage {
                display: none;
            }
            a {
                text-decoration: underline;
                color: blue;
            }
        </style>
    </head>

    <body>

        <div id="images">
            $images
        </div>

        <div id="listing">
            <h2>$title</h2>
            $listing
        </div>

    </body>

</html>
"""


def make_page(folder, overwrite):
    """
    Takes a path to a folder and creates an HTML summary page at index.html within it.
    """
    abs_folder = os.path.abspath(folder)
    outfile = os.path.join(abs_folder, 'index.html')
    if os.path.exists(outfile) and not overwrite:
        print("File {} already exists - ABORTING".format(outfile))
        sys.exit(1)

    conn_folders = []
    conn_regex = re.compile("c([0-9]+)")
    for f in os.listdir(abs_folder):
        match = conn_regex.match(f)
        if match:
            conn_folders.append(int(match.group(1)))

    if not conn_folders:
        print("This doesn't look like textual flow data - expecting at least one cXXX folder")
        sys.exit(2)

    conn_folders.sort()

    image_structure = ""
    for f in conn_folders:
        image_structure += '''
            <div class="showhideimage">
                <h3><a onclick="showhide(\'c{}\')">+/- c{}</a></h3>
                <div id="c{}" style="image"></div>
            </div>
        '''.format(f, f, f)

    svg_files = [x for x in os.listdir(os.path.join(abs_folder, 'c{}'.format(conn_folders[0])))
                 if os.path.splitext(x)[1] == '.svg']
    print("Found {} SVG files in c{}".format(len(svg_files), conn_folders[0]))
    parsed_svg_files = []
    svg_re = re.compile("textual_flow_B([0-9]{2})K([0-9]{2})V([0-9]{2})_([^-,]+)[-,]?(.*?)_c[0-9]+\.svg")
    for svg in svg_files:
        match = svg_re.match(svg)
        if not match:
            print("WARNING: File doesn't match pattern: {} - IGNORING".format(svg))
            continue

        ref = [int(x) for x in match.groups()[:-1]]
        ref.append(match.group(5))  # this isn't reliably an integer...
        parsed_svg_files.append(tuple(ref))

    parsed_svg_files.sort()

    listing = []
    for b, k, v, ws, we in parsed_svg_files:
        w = str(ws)
        if we:
            w += '-{}'.format(we)
        listing.append('''<a onclick="showref({B:02d}, {K:02d}, {V:02d}, {S}, {E})">
                            B{B:02d}K{K:02d}V{V:02d}/{W}
                          </a><br/>'''
                       .format(B=b, K=k, V=v, S=ws, E=we, W=w))

    data = {
        'title': os.path.basename(abs_folder),
        'jquery': JQUERY,
        'listing': '\n'.join(listing),
        'images': image_structure,
    }

    html = string.Template(HTML_TEMPLATE).substitute(data)


    with open(outfile, 'w') as f:
        f.write(html)

    shutil.copyfile(os.path.join(HERE, JQUERY), os.path.join(folder, JQUERY))

    print("Done - please see {}".format(outfile))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Textual flow HTML summary generator")
    parser.add_argument('folder', help="Folder containing textual flow data (must contain cXXX folders")
    parser.add_argument('--overwrite', action='store_true', help="Overwrite an existing file")
    args = parser.parse_args()
    make_page(args.folder, args.overwrite)
