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
        <meta content="text/html; charset=UTF-8" http-equiv="Content-Type">
        <script src="$jquery"></script>
        <style>
            body {
                font-size: 10pt;
                font-family: arial, sans-serif;
            }
            div#listing {
                min-width: 10%;
                max-width: 20%;
                border-right: 1px dashed grey;
                height: 100%;
                overflow: auto;
                }
            div#images {
                display: none;
                min-width: 80%;
                max-width: 89%;
                float: right;
                margin-left: 10px;
                height: 100%;
                overflow: auto;
                }
            img.image {
                border: 1px solid grey;
                width: 98%;
            }
            a {
                text-decoration: underline;
                color: blue;
            }
        </style>
        <script>
            var conn_values = $conn_values;
            function showvariant(book, chapter, verse, word, suffix) {
                for (i = 0; i < conn_values.length; ++i) {
                    var cv = conn_values[i];
                    if (suffix) {
                        suff_bit = '_' + suffix;
                    } else {
                        suff_bit = '';
                    }
                    var tf = cv + '/textual_flow_B' + book + 'K' + chapter + 'V' + verse + '_' + word + '_' + cv + suff_bit + '.svg';
                    $$("img#" + cv).attr('src', tf);
                    $$("a#" + cv).attr('href', tf);
                    $$("h3#" + cv).text(tf);
                    console.log(tf);
                }
                $$("#images").show();
            }
        </script>
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
    conn_regex = re.compile("c([0-9]+(perc)?)")
    for f in os.listdir(abs_folder):
        match = conn_regex.match(f)
        if match:
            conn_folders.append(match.group(1))

    if not conn_folders:
        print("This doesn't look like textual flow data - expecting at least one cXXX folder")
        sys.exit(2)

    def sortme(x):
        if x.endswith('perc'):
            return 10000 - int(x[:-4])
        else:
            return int(x)

    conn_folders.sort(key=sortme)

    image_structure = ""
    for f in conn_folders:
        sanitised_f = f.replace('%', 'perc')
        image_structure += '''
            <h3 id="c{}"></h3>
            <a id="c{}" target="_blank"><img id="c{}" class="image"/></a>
        '''.format(sanitised_f, sanitised_f, sanitised_f, sanitised_f)

    svg_files = [x for x in os.listdir(os.path.join(abs_folder, 'c{}'.format(conn_folders[0])))
                 if os.path.splitext(x)[1] == '.svg']
    print("Found {} SVG files in c{}".format(len(svg_files), conn_folders[0]))
    parsed_svg_files = []
    svg_re = re.compile("textual_flow_B([0-9]{2})K([0-9]{2})V([0-9]{2})_([^-,]+)[-,]?(.*?)_c[0-9]+_?(.*)\.svg")
    for svg in svg_files:
        match = svg_re.match(svg)
        if not match:
            print("WARNING: File doesn't match pattern: {} - IGNORING".format(svg))
            continue

        ref = [int(x) for x in match.groups()[:-2]]
        ref.append(match.group(5))  # this isn't reliably an integer...
        ref.append(match.group(6))  # optional suffix: this isn't an integer...
        parsed_svg_files.append(tuple(ref))

    parsed_svg_files.sort()

    listing = []
    prev_verse = None
    for b, k, v, ws, we, suffix in parsed_svg_files:
        w = str(ws)
        if we:
            w += '-{}'.format(we)
        vref = (b, k, v)
        if prev_verse != vref:
            listing.append("<h3>B{B:02d}K{K:02d}V{V:02d}</h3>".format(B=b, K=k, V=v))
            prev_verse = vref

        listing.append('''<a onclick="showvariant('{B:02d}', '{K:02d}', '{V:02d}', '{W}', '{suffix}')">
                            B{B:02d}K{K:02d}V{V:02d}/{W} {suffix}
                          </a><br/>'''
                       .format(B=b, K=k, V=v, W=w, suffix=suffix))

    data = {
        'title': os.path.basename(abs_folder),
        'jquery': JQUERY,
        'listing': '\n'.join(listing),
        'conn_values': ['c{}'.format(x) for x in conn_folders],
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
