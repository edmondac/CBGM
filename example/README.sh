#!/bin/bash
set -e
set -x

# This readme is executable as a test script... it will create the documented
# output.

# Various of these commands can also use MPI - just do "mpirun -n 4 [cmd]"

### Populate database ###
../populate_db example_input.py --force /tmp/test.db
#~ Will populate /tmp/test.db
#~ Wrote 41 variant units


### Pre-genealogical coherence ###
../cbgm -d /tmp/test.db -P -w P75
#~ Using database: /tmp/test.db
#~ Pre-genealogicalcoherenceforW1=P75
#~ W2  NR  PERC1   EQ  PASS
#~ 019 1   97.143  34  35
#~ 03  2   94.444  34  36
#~ A   3   93.333  14  15
#~ 091 4   88.889  16  18
#~ 022 5   88.571  31  35
#~ 044 6   86.111  31  36
#~ 032 7   85.714  30  35
#~ 0141    8   83.333  30  36
#~ 02      83.333  30  36
#~ 063 10  82.143  23  28
#~ 011 11  80.556  29  36
#~ 037 12  80.000  28  35
#~ 031     80.000  24  30
#~ 017 14  77.778  28  36
#~ 021     77.778  28  36
#~ 07      77.778  28  36
#~ 028 17  75.000  27  36
#~ 034     75.000  27  36
#~ 036     75.000  27  36
#~ 045     75.000  27  36
#~ 047     75.000  27  36
#~ 05  22  72.414  21  29
#~ 013 23  72.222  26  36
#~ 0211        72.222  26  36
#~ 030     72.222  26  36
#~ 038     72.222  26  36
#~ 01  27  42.424  14  33


### Genealogical coherence ###
../cbgm -d /tmp/test.db -G -w P75
#~ Using database: /tmp/test.db
#~ PotentialancestorsforW1=P75
#~ W2  NR  D   PERC1   EQ  PASS    W1<W2   W1>W2   UNCL    NOREL
#~ 019 0   -   97.143  34  35  0   0   1   0
#~ 03  0   -   94.444  34  36  0   0   2   0
#~ A   1       93.333  14  15  1   0   0   0
#~ 091 0   -   88.889  16  18  0   0   2   0


### Local Stemmata ###
../cbgm -d /tmp/test.db -L -v 21/2
#~ Using database: /tmp/test.db
#~ Creating graph with 2 nodes and 1 edges
#~ Couldn't import dot_parser, loading of dot files will not be possible.
#~ Written diagram to 21_2.svg
#~ label   text    witnesses
#~ a   ηθελον  𝔓75, 02, 03, 05, 07, 011, 013, 017, 019, 021, 022, 028, 030, 031, 032, 034, 036, 037, 038, 044, 045, 047, 063, 0141, 0211
#~ b   ηλθον   01
    #~ lac 091

#~ ** See examples/21_2.svg


### Textual flow diagram ###
../cbgm -d /tmp/test.db -T -v all -c 2,499
#~ [2017-01-26 22:10:11,364] [7317] [cbgm.py:125] [INFO] Using database: /tmp/test.db
#~ [2017-01-26 22:10:11,385] [7317] [textual_flow.py:215] [INFO] Creating textual flow diagram for 22/20
#~ [2017-01-26 22:10:11,385] [7317] [textual_flow.py:216] [INFO] Setting connectivity to [2, 499]
#~ [2017-01-26 22:10:11,386] [7317] [textual_flow.py:58] [INFO] Getting best parent(s) for 044
#~ [2017-01-26 22:10:11,441] [7317] [textual_flow.py:74] [INFO] Calculating for conn=2
#~ [2017-01-26 22:10:11,441] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=2): []
#~ [2017-01-26 22:10:11,442] [7317] [textual_flow.py:74] [INFO] Calculating for conn=499
#~ [2017-01-26 22:10:11,442] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=499): []
#~ [2017-01-26 22:10:11,442] [7317] [textual_flow.py:58] [INFO] Getting best parent(s) for 034
#~ [2017-01-26 22:10:11,496] [7317] [textual_flow.py:74] [INFO] Calculating for conn=2
#~ [2017-01-26 22:10:11,496] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=2): [('07', 1, 1)]
#~ [2017-01-26 22:10:11,496] [7317] [textual_flow.py:74] [INFO] Calculating for conn=499
#~ [2017-01-26 22:10:11,496] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=499): [('07', 1, 1)]
#~ [2017-01-26 22:10:11,497] [7317] [textual_flow.py:58] [INFO] Getting best parent(s) for 036
#~ [2017-01-26 22:10:11,548] [7317] [textual_flow.py:74] [INFO] Calculating for conn=2
#~ [2017-01-26 22:10:11,549] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=2): [('021', 1, 1)]
#~ [2017-01-26 22:10:11,549] [7317] [textual_flow.py:74] [INFO] Calculating for conn=499
#~ [2017-01-26 22:10:11,549] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=499): [('021', 1, 1)]
#~ [2017-01-26 22:10:11,549] [7317] [textual_flow.py:58] [INFO] Getting best parent(s) for 045
#~ [2017-01-26 22:10:11,602] [7317] [textual_flow.py:74] [INFO] Calculating for conn=2
#~ [2017-01-26 22:10:11,602] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=2): [('063', 1, 1)]
#~ [2017-01-26 22:10:11,602] [7317] [textual_flow.py:74] [INFO] Calculating for conn=499
#~ [2017-01-26 22:10:11,603] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=499): [('063', 1, 1)]
#~ [2017-01-26 22:10:11,603] [7317] [textual_flow.py:58] [INFO] Getting best parent(s) for 047
#~ [2017-01-26 22:10:11,656] [7317] [textual_flow.py:74] [INFO] Calculating for conn=2
#~ [2017-01-26 22:10:11,656] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=2): [('021', 1, 1)]
#~ [2017-01-26 22:10:11,656] [7317] [textual_flow.py:74] [INFO] Calculating for conn=499
#~ [2017-01-26 22:10:11,656] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=499): [('021', 1, 1)]
#~ [2017-01-26 22:10:11,657] [7317] [textual_flow.py:58] [INFO] Getting best parent(s) for 013
#~ [2017-01-26 22:10:11,711] [7317] [textual_flow.py:74] [INFO] Calculating for conn=2
#~ [2017-01-26 22:10:11,711] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=2): [('031', 1, 1)]
#~ [2017-01-26 22:10:11,711] [7317] [textual_flow.py:74] [INFO] Calculating for conn=499
#~ [2017-01-26 22:10:11,711] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=499): [('031', 1, 1)]
#~ [2017-01-26 22:10:11,712] [7317] [textual_flow.py:58] [INFO] Getting best parent(s) for 011
#~ [2017-01-26 22:10:11,762] [7317] [textual_flow.py:74] [INFO] Calculating for conn=2
#~ [2017-01-26 22:10:11,762] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=2): [('063', 1, 1)]
#~ [2017-01-26 22:10:11,763] [7317] [textual_flow.py:74] [INFO] Calculating for conn=499
#~ [2017-01-26 22:10:11,763] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=499): [('063', 1, 1)]
#~ [2017-01-26 22:10:11,763] [7317] [textual_flow.py:58] [INFO] Getting best parent(s) for 028
#~ [2017-01-26 22:10:11,815] [7317] [textual_flow.py:74] [INFO] Calculating for conn=2
#~ [2017-01-26 22:10:11,815] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=2): [('063', 1, 1)]
#~ [2017-01-26 22:10:11,815] [7317] [textual_flow.py:74] [INFO] Calculating for conn=499
#~ [2017-01-26 22:10:11,816] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=499): [('063', 1, 1)]
#~ [2017-01-26 22:10:11,816] [7317] [textual_flow.py:58] [INFO] Getting best parent(s) for 030
#~ [2017-01-26 22:10:11,869] [7317] [textual_flow.py:74] [INFO] Calculating for conn=2
#~ [2017-01-26 22:10:11,869] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=2): [('07', 1, 1)]
#~ [2017-01-26 22:10:11,869] [7317] [textual_flow.py:74] [INFO] Calculating for conn=499
#~ [2017-01-26 22:10:11,869] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=499): [('07', 1, 1)]
#~ [2017-01-26 22:10:11,870] [7317] [textual_flow.py:58] [INFO] Getting best parent(s) for 021
#~ [2017-01-26 22:10:11,921] [7317] [textual_flow.py:74] [INFO] Calculating for conn=2
#~ [2017-01-26 22:10:11,921] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=2): [('063', 1, 1)]
#~ [2017-01-26 22:10:11,921] [7317] [textual_flow.py:74] [INFO] Calculating for conn=499
#~ [2017-01-26 22:10:11,922] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=499): [('063', 1, 1)]
#~ [2017-01-26 22:10:11,922] [7317] [textual_flow.py:58] [INFO] Getting best parent(s) for 0141
#~ [2017-01-26 22:10:11,973] [7317] [textual_flow.py:74] [INFO] Calculating for conn=2
#~ [2017-01-26 22:10:11,973] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=2): [('044', 1, 1)]
#~ [2017-01-26 22:10:11,973] [7317] [textual_flow.py:74] [INFO] Calculating for conn=499
#~ [2017-01-26 22:10:11,974] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=499): [('044', 1, 1)]
#~ [2017-01-26 22:10:11,974] [7317] [textual_flow.py:58] [INFO] Getting best parent(s) for 031
#~ [2017-01-26 22:10:12,020] [7317] [textual_flow.py:74] [INFO] Calculating for conn=2
#~ [2017-01-26 22:10:12,020] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=2): [('063', 1, 1)]
#~ [2017-01-26 22:10:12,020] [7317] [textual_flow.py:74] [INFO] Calculating for conn=499
#~ [2017-01-26 22:10:12,020] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=499): [('063', 1, 1)]
#~ [2017-01-26 22:10:12,021] [7317] [textual_flow.py:58] [INFO] Getting best parent(s) for 063
#~ [2017-01-26 22:10:12,062] [7317] [textual_flow.py:74] [INFO] Calculating for conn=2
#~ [2017-01-26 22:10:12,062] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=2): []
#~ [2017-01-26 22:10:12,062] [7317] [textual_flow.py:74] [INFO] Calculating for conn=499
#~ [2017-01-26 22:10:12,063] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=499): []
#~ [2017-01-26 22:10:12,063] [7317] [textual_flow.py:58] [INFO] Getting best parent(s) for 07
#~ [2017-01-26 22:10:12,129] [7317] [textual_flow.py:74] [INFO] Calculating for conn=2
#~ [2017-01-26 22:10:12,130] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=2): [('063', 1, 1)]
#~ [2017-01-26 22:10:12,130] [7317] [textual_flow.py:74] [INFO] Calculating for conn=499
#~ [2017-01-26 22:10:12,130] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=499): [('063', 1, 1)]
#~ [2017-01-26 22:10:12,131] [7317] [textual_flow.py:58] [INFO] Getting best parent(s) for 017
#~ [2017-01-26 22:10:12,186] [7317] [textual_flow.py:74] [INFO] Calculating for conn=2
#~ [2017-01-26 22:10:12,186] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=2): [('031', 1, 1)]
#~ [2017-01-26 22:10:12,186] [7317] [textual_flow.py:74] [INFO] Calculating for conn=499
#~ [2017-01-26 22:10:12,186] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=499): [('031', 1, 1)]
#~ [2017-01-26 22:10:12,187] [7317] [textual_flow.py:58] [INFO] Getting best parent(s) for 03
#~ [2017-01-26 22:10:12,237] [7317] [textual_flow.py:74] [INFO] Calculating for conn=2
#~ [2017-01-26 22:10:12,237] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=2): []
#~ [2017-01-26 22:10:12,237] [7317] [textual_flow.py:74] [INFO] Calculating for conn=499
#~ [2017-01-26 22:10:12,237] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=499): []
#~ [2017-01-26 22:10:12,238] [7317] [textual_flow.py:58] [INFO] Getting best parent(s) for 02
#~ [2017-01-26 22:10:12,291] [7317] [textual_flow.py:74] [INFO] Calculating for conn=2
#~ [2017-01-26 22:10:12,292] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=2): [('03', 1, 1)]
#~ [2017-01-26 22:10:12,292] [7317] [textual_flow.py:74] [INFO] Calculating for conn=499
#~ [2017-01-26 22:10:12,292] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=499): [('03', 1, 1)]
#~ [2017-01-26 22:10:12,292] [7317] [textual_flow.py:58] [INFO] Getting best parent(s) for 038
#~ [2017-01-26 22:10:12,347] [7317] [textual_flow.py:74] [INFO] Calculating for conn=2
#~ [2017-01-26 22:10:12,348] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=2): []
#~ [2017-01-26 22:10:12,348] [7317] [textual_flow.py:74] [INFO] Calculating for conn=499
#~ [2017-01-26 22:10:12,348] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=499): [('03', 8, 1)]
#~ [2017-01-26 22:10:12,348] [7317] [textual_flow.py:58] [INFO] Getting best parent(s) for P75
#~ [2017-01-26 22:10:12,400] [7317] [textual_flow.py:74] [INFO] Calculating for conn=2
#~ [2017-01-26 22:10:12,400] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=2): []
#~ [2017-01-26 22:10:12,400] [7317] [textual_flow.py:74] [INFO] Calculating for conn=499
#~ [2017-01-26 22:10:12,400] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=499): []
#~ [2017-01-26 22:10:12,401] [7317] [textual_flow.py:58] [INFO] Getting best parent(s) for 01
#~ [2017-01-26 22:10:12,474] [7317] [textual_flow.py:74] [INFO] Calculating for conn=2
#~ [2017-01-26 22:10:12,474] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=2): []
#~ [2017-01-26 22:10:12,474] [7317] [textual_flow.py:74] [INFO] Calculating for conn=499
#~ [2017-01-26 22:10:12,475] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=499): [('05', 25, 1)]
#~ [2017-01-26 22:10:12,475] [7317] [textual_flow.py:58] [INFO] Getting best parent(s) for 05
#~ [2017-01-26 22:10:12,531] [7317] [textual_flow.py:74] [INFO] Calculating for conn=2
#~ [2017-01-26 22:10:12,531] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=2): []
#~ [2017-01-26 22:10:12,531] [7317] [textual_flow.py:74] [INFO] Calculating for conn=499
#~ [2017-01-26 22:10:12,531] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=499): []
#~ [2017-01-26 22:10:12,532] [7317] [textual_flow.py:58] [INFO] Getting best parent(s) for 0211
#~ [2017-01-26 22:10:12,589] [7317] [textual_flow.py:74] [INFO] Calculating for conn=2
#~ [2017-01-26 22:10:12,589] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=2): []
#~ [2017-01-26 22:10:12,589] [7317] [textual_flow.py:74] [INFO] Calculating for conn=499
#~ [2017-01-26 22:10:12,589] [7317] [textual_flow.py:125] [INFO] Found best parents (conn=499): []
#~ [2017-01-26 22:10:12,590] [7317] [textual_flow.py:291] [WARNING] 044 has no parents
#~ [2017-01-26 22:10:12,590] [7317] [textual_flow.py:291] [WARNING] 063 has no parents
#~ [2017-01-26 22:10:12,590] [7317] [textual_flow.py:291] [WARNING] 03 has no parents
#~ [2017-01-26 22:10:12,590] [7317] [textual_flow.py:291] [WARNING] 038 has no parents
#~ [2017-01-26 22:10:12,590] [7317] [textual_flow.py:291] [WARNING] P75 has no parents
#~ [2017-01-26 22:10:12,590] [7317] [textual_flow.py:291] [WARNING] 01 has no parents
#~ [2017-01-26 22:10:12,591] [7317] [textual_flow.py:291] [WARNING] 05 has no parents
#~ [2017-01-26 22:10:12,591] [7317] [textual_flow.py:291] [WARNING] 0211 has no parents
#~ [2017-01-26 22:10:12,592] [7317] [textual_flow.py:301] [INFO] Creating graph with 22 nodes and 14 edges
#~ Couldn't import dot_parser, loading of dot files will not be possible.
#~ [2017-01-26 22:10:12,704] [7317] [textual_flow.py:307] [INFO] Written to textual_flow_22_20_c2.svg
#~ [2017-01-26 22:10:12,705] [7317] [textual_flow.py:291] [WARNING] 044 has no parents
#~ [2017-01-26 22:10:12,705] [7317] [textual_flow.py:291] [WARNING] 063 has no parents
#~ [2017-01-26 22:10:12,705] [7317] [textual_flow.py:291] [WARNING] 03 has no parents
#~ [2017-01-26 22:10:12,705] [7317] [textual_flow.py:291] [WARNING] P75 has no parents
#~ [2017-01-26 22:10:12,705] [7317] [textual_flow.py:291] [WARNING] 05 has no parents
#~ [2017-01-26 22:10:12,705] [7317] [textual_flow.py:291] [WARNING] 0211 has no parents
#~ [2017-01-26 22:10:12,706] [7317] [textual_flow.py:301] [INFO] Creating graph with 22 nodes and 16 edges
#~ [2017-01-26 22:10:12,778] [7317] [textual_flow.py:307] [INFO] Written to textual_flow_22_20_c499.svg

#~ ** See examples/textual_flow_22_20_c2.svg and examples/textual_flow_22_20_c499.svg


### Stripes (summary of attestations) ###
../stripes.py /tmp/test.db
#~ Using database: /tmp/test.db
#~ A a???aa?a?bb?aaaaba?a?a?a???????a????a???a
#~ P75 aab?aaaab?b???aaaabaaaaabaaaaaaaaabaaaaba
#~ 01 baabbaabcaaaabbababacab??bbab?bbbabaacbca
#~ 02 aabaaaaab?b???abaabaaaabaaabaaaaaaaaaaaaa
#~ 03 aabaaaaab?b???aaaabaaaaacaaaaaaaaaaaaaaba
#~ 05 abcaaaaacbaaacaaaabbaac??aacaaaaa??b???ba
#~ 07 aaaaaaaaaaaaaaaaaaaaaaabaaaaaaaaaaaaaaaaa
#~ 011 aabaaaaaaaaaaaaaaaaaaaabaaaaaaaaaaaaaaaaa
#~ 013 aaaaaaaaaaaaaaaaaaaaaaabaaaaabacaaaaaaaaa
#~ 017 aaaaaaaaaaaaaaaaaabaaaabfaaaaaaaaaaaaaaab
#~ 019 aabaaaaa??b???aaaabaaaaahaaaaaaaaabaaaaba
#~ 021 aaaaaaaaaaaaaaaaaaaaaaabdaaaaaaaaaaaaaaaa
#~ 022 aabaaaaa??b???aaaabaababeaaaaaaaaaaaaaaba
#~ 028 aaaaaaaaaaaaaaaaaaaaaaabaaaaaaaaaaaaacaaa
#~ 030 aaaaaaaaaaaaaaaaaaaaaaabaaaaacaaaaaabaaaa
#~ 031 aaaaaaaaaaaaaaaaaa?a??a?aaaaaa??aaaaaaaaa
#~ 032 abbaaaaa??b???aaaabaaaabccaaaaaaaaaaaaaba
#~ 034 aaaaaaaaaaabaaaaabaaaaabaaaaaaaaaaaaaaaaa
#~ 036 aaaaaaaaaaaaaaaaaaaaaaabdaaaaaaaaaaabaaaa
#~ 037 aaaaaaaa?aaabaaaaaaaaaabaaaaaaaaaaaaaaaaa
#~ 038 aaaaaababaaaaaaaaaaabaabaaaaaaabaaaaaaaaa
#~ 044 abbaaaaaa?b???aaaabaaaabgaaaaaaaaaaaaaaba
#~ 045 aaaaaabaaaaaaaaaaaaaaaabaaaaaaaaaaaaaaaaa
#~ 047 aaaaaaaaaaaabaaaaaabaaabdaaaaaaaaaaaaaaaa
#~ 063 aaaaaaaaa?b???aaaaaaaaabaaaaaaa???????a?a
#~ 091 ??????????????aaaabaaaaadaacaaaa?????????
#~ 0141 aabaaaaaaaaaaaaaaabaaaabiaaaaaaaaaaaaaaaa
#~ 0211 aaababaadbaaaaaaaabaaaabaaaaaaaaabaabaaaa


### Summary of variant units ###
../cbgm -d /tmp/test.db -X -w P75
#~ Using database: /tmp/test.db
#~ All variant units (41): 21/2, 21/6-8, 21/20-24, 21/28-30, 21/36, 22/3, 22/10, 22/12, 22/20, 22/40, 22/40-52, 22/42, 22/46, 22/52, 22/60, 22/61, 22/62-66, 22/68-70, 22/76, 22/80, 22/88, 23/1, 23/2-10, 23/3, 23/4-10, 23/12-16, 23/20-22, 23/26-30, 24/2-10, 24/6, 24/14, 24/14-20, 24/28, 24/30, 24/30-32, 24/30-38, 24/31, 24/32, 24/36, 24/38, 24/50-52

#~ 21/6-8 is unresolved (2 unclear parents)
#~ 21/20-24 is unresolved (3 unclear parents)
#~ 21/28-30 is unresolved (2 unclear parents)
#~ 22/10 is unresolved (2 unclear parents)
#~ 22/20 is unresolved (4 unclear parents)
#~ 22/42 is unresolved (2 unclear parents)
#~ 22/76 is unresolved (2 unclear parents)
#~ 22/88 is unresolved (3 unclear parents)
#~ 23/2-10 is unresolved (3 unclear parents)
#~ 23/4-10 is unresolved (9 unclear parents)
#~ 23/12-16 is unresolved (3 unclear parents)
#~ 23/20-22 is unresolved (2 unclear parents)
#~ 23/26-30 is unresolved (2 unclear parents)
#~ 24/2-10 is unresolved (2 unclear parents)
#~ 24/6 is unresolved (2 unclear parents)
#~ 24/14-20 is unresolved (2 unclear parents)
#~ 24/28 is unresolved (2 unclear parents)
#~ 24/30 is unresolved (2 unclear parents)
#~ 24/30-32 is unresolved (2 unclear parents)
#~ 24/30-38 is unresolved (2 unclear parents)
#~ 24/32 is unresolved (2 unclear parents)
#~ 24/36 is unresolved (2 unclear parents)
#~ 24/38 is unresolved (3 unclear parents)

#~ There are 23 unresolved variant units


### Hypotheses on unclear ###
# This script creates textual flow diagrams for all conceivable hypotheses for
# currently UNCL relationships in a specified variant unit.
../hypotheses_on_unclear -s -v 21/28-30 example_input.py
#~ Will populate 21.28-30_0.db
#~ Wrote 41 variant units
#~ Creating textual flow diagram for 21/28-30
#~ Setting connectivity to 499
#~ Calculating genealogical coherence for A at 21/28-30
#~ Calculating genealogical coherence for 063 at 21/28-30
#~ Calculating genealogical coherence for 045 at 21/28-30
#~ Calculating genealogical coherence for 022 at 21/28-30
#~ Calculating genealogical coherence for 047 at 21/28-30
#~ Calculating genealogical coherence for 011 at 21/28-30
#~ Calculating genealogical coherence for 038 at 21/28-30
#~ Calculating genealogical coherence for 013 at 21/28-30
#~ Calculating genealogical coherence for 021 at 21/28-30
#~ Calculating genealogical coherence for 017 at 21/28-30
#~ Calculating genealogical coherence for 032 at 21/28-30
#~ Calculating genealogical coherence for 019 at 21/28-30
#~ Calculating genealogical coherence for 030 at 21/28-30
#~ Calculating genealogical coherence for 031 at 21/28-30
#~ Calculating genealogical coherence for 036 at 21/28-30
#~ Calculating genealogical coherence for 037 at 21/28-30
#~ Calculating genealogical coherence for 034 at 21/28-30
#~ Calculating genealogical coherence for 02 at 21/28-30
#~ Calculating genealogical coherence for 03 at 21/28-30
#~ Calculating genealogical coherence for 044 at 21/28-30
#~ Calculating genealogical coherence for 07 at 21/28-30
#~ Calculating genealogical coherence for 05 at 21/28-30
#~ Calculating genealogical coherence for 028 at 21/28-30
#~ Calculating genealogical coherence for 0141 at 21/28-30
#~ Calculating genealogical coherence for 0211 at 21/28-30
#~ Calculating genealogical coherence for 01 at 21/28-30
#~ Creating graph with 26 nodes and 25 edges
#~ Couldn't import dot_parser, loading of dot files will not be possible.
#~ Written to textual_flow_21_28-30_c499.svg
#~ Will populate 21.28-30_1.db
#~ Wrote 41 variant units
#~ Creating textual flow diagram for 21/28-30
#~ Setting connectivity to 499
#~ Calculating genealogical coherence for 063 at 21/28-30
#~ Calculating genealogical coherence for 045 at 21/28-30
#~ Calculating genealogical coherence for 022 at 21/28-30
#~ Calculating genealogical coherence for 047 at 21/28-30
#~ Calculating genealogical coherence for 011 at 21/28-30
#~ Calculating genealogical coherence for 038 at 21/28-30
#~ Calculating genealogical coherence for 013 at 21/28-30
#~ Calculating genealogical coherence for 021 at 21/28-30
#~ Calculating genealogical coherence for 017 at 21/28-30
#~ Calculating genealogical coherence for 032 at 21/28-30
#~ Calculating genealogical coherence for 019 at 21/28-30
#~ Calculating genealogical coherence for 030 at 21/28-30
#~ Calculating genealogical coherence for 031 at 21/28-30
#~ Calculating genealogical coherence for 036 at 21/28-30
#~ Calculating genealogical coherence for 037 at 21/28-30
#~ Calculating genealogical coherence for 034 at 21/28-30
#~ Calculating genealogical coherence for 02 at 21/28-30
#~ Calculating genealogical coherence for 03 at 21/28-30
#~ Calculating genealogical coherence for 044 at 21/28-30
#~ Calculating genealogical coherence for 07 at 21/28-30
#~ Calculating genealogical coherence for 05 at 21/28-30
#~ Calculating genealogical coherence for 028 at 21/28-30
#~ Calculating genealogical coherence for 0141 at 21/28-30
#~ Calculating genealogical coherence for 0211 at 21/28-30
#~ Calculating genealogical coherence for A at 21/28-30
#~ Calculating genealogical coherence for 01 at 21/28-30
#~ Creating graph with 26 nodes and 25 edges
#~ Written to textual_flow_21_28-30_c499.svg
#~ Opening browser...
#~ View the files in /tmp/tmpGqDCWX/index.html


#~ ** See hypotheses/index.html


### Combinations of Ancestors ###
../cbgm -d /tmp/test.db -A -w 05 --max-comb-len=100000 --csv
#~ Using database: /tmp/test.db
#~ Found 20 potential ancestors for 05
#~ Witness 05 has reading 'a' at 21/2 with parent INIT
#~ Witness 05 has reading 'b' at 21/6-8 with parent UNCL
#~ Witness 05 has reading 'c' at 21/20-24 with parent UNCL
#~ Witness 05 has reading 'a' at 21/28-30 with parent UNCL
#~ Witness 05 has reading 'a' at 21/36 with parent INIT
#~ Witness 05 has reading 'a' at 22/3 with parent INIT
#~ Witness 05 has reading 'a' at 22/10 with parent UNCL
#~ Witness 05 has reading 'a' at 22/12 with parent INIT
#~ Witness 05 has reading 'c' at 22/20 with parent UNCL
#~ Witness 05 has reading 'b' at 22/40 with parent INIT
#~ Witness 05 has reading 'a' at 22/40-52 with parent b
#~ Witness 05 has reading 'a' at 22/42 with parent UNCL
#~ Witness 05 has reading 'a' at 22/46 with parent INIT
#~ Witness 05 has reading 'c' at 22/52 with parent a
#~ Witness 05 has reading 'c' at 23/2-10 with parent UNCL
#~ Witness 05 has reading 'a' at 24/28 with parent UNCL
#~ Witness 05 has reading 'b' at 24/30-38 with parent UNCL
#~ Witness 05 has reading 'b' at 24/38 with parent UNCL
#~ Witness 05 has reading 'a' at 24/50-52 with parent INIT
#~ Witness 05 has reading 'c' at 23/26-30 with parent UNCL
#~ Witness 05 has reading 'a' at 23/12-16 with parent UNCL
#~ Witness 05 has reading 'b' at 22/76 with parent UNCL
#~ Witness 05 has reading 'a' at 22/88 with parent UNCL
#~ Witness 05 has reading 'a' at 23/20-22 with parent UNCL
#~ Witness 05 has reading 'a' at 24/2-10 with parent UNCL
#~ Witness 05 has reading 'a' at 24/6 with parent UNCL
#~ Witness 05 has reading 'a' at 24/14-20 with parent UNCL
#~ Witness 05 has reading 'a' at 23/1 with parent INIT
#~ Witness 05 has reading 'a' at 24/14 with parent INIT
#~ Witness 05 has reading 'a' at 22/61 with parent INIT
#~ 1000000/1000000 (100.00%) (Time taken: 6.0m, remaining 0s)  See 05.csv
#~ ed@roo:~/PhD/CBGM_ace/example$ ls -lah 05.csv
#~ -rw-rw-r-- 1 ed ed 324M Sep  8 11:28 05.csv

#~ ** file deleted as it's so big!


### Apparatus ###
../apparatus.py  /tmp/test.db
#~ Using database: /tmp/test.db

#~ 21/2
#~ a ηθελον A, P75, 02, 03, 05, 07, 011, 013, 017, 019, 021, 022, 028, 030, 031, 032, 034, 036, 037, 038, 044, 045, 047, 063, 0141, 0211
#~ b ηλθον 01

#~ 21/6-8
#~ a λαβειν αυτον P75, 01, 02, 03, 07, 011, 013, 017, 019, 021, 022, 028, 030, 031, 034, 036, 037, 038, 045, 047, 063, 0141, 0211
#~ b αυτον λαβειν 05, 032, 044

#~ 21/20-24
#~ a το πλοιον εγενετο 01, 07, 013, 017, 021, 028, 030, 031, 034, 036, 037, 038, 045, 047, 063, 0211
#~ b εγενετο το πλοιον P75, 02, 03, 011, 019, 022, 032, 044, 0141
#~ c το πλοιον εγενηθη 05

#~ 21/28-30
#~ a της γης 02, 03, 05, 07, 011, 013, 017, 019, 021, 022, 028, 030, 031, 032, 034, 036, 037, 038, 044, 045, 047, 063, 0141
#~ b την γην 01, 0211

#~ 21/36
#~ a υπηγον A, P75, 02, 03, 05, 07, 011, 013, 017, 019, 021, 022, 028, 030, 031, 032, 034, 036, 037, 038, 044, 045, 047, 063, 0141, 0211
#~ b υπηντησεν 01

#~ 22/3
#~ a  A, P75, 01, 02, 03, 05, 07, 011, 013, 017, 019, 021, 022, 028, 030, 031, 032, 034, 036, 037, 038, 044, 045, 047, 063, 0141
#~ b τε 0211

#~ 22/10
#~ a ο P75, 01, 02, 03, 05, 07, 011, 013, 017, 019, 021, 022, 028, 030, 031, 032, 034, 036, 037, 044, 047, 063, 0141, 0211
#~ b  038, 045

#~ 22/12
#~ a εστηκως A, P75, 02, 03, 05, 07, 011, 013, 017, 019, 021, 022, 028, 030, 031, 032, 034, 036, 037, 038, 044, 045, 047, 063, 0141, 0211
#~ b εστως 01

#~ 22/20
#~ a ιδων 07, 011, 013, 017, 021, 028, 030, 031, 034, 036, 044, 045, 047, 063, 0141
#~ b ειδον P75, 02, 03, 038
#~ c ειδεν 01, 05
#~ d ειδως 0211

#~ 22/40
#~ b  05, 0211
#~ a εκεινο 01, 07, 011, 013, 017, 021, 028, 030, 031, 034, 036, 037, 038, 045, 047, 0141

#~ 22/40-52
#~ b  A, P75, 02, 03, 019, 022, 032, 044, 063
#~ a εκεινο εις ο ενεβησαν οι μαθηται αυτου 01, 05, 07, 011, 013, 017, 021, 028, 030, 031, 034, 036, 037, 038, 045, 047, 0141, 0211

#~ 22/42
#~ a εις 01, 05, 07, 011, 013, 017, 021, 028, 030, 031, 036, 037, 038, 045, 047, 0141, 0211
#~ b  034

#~ 22/46
#~ a ενεβησαν 01, 05, 07, 011, 013, 017, 021, 028, 030, 031, 034, 036, 038, 045, 0141, 0211
#~ b ανεβησαν 037, 047

#~ 22/52
#~ a αυτου 07, 011, 013, 017, 021, 028, 030, 031, 034, 036, 037, 038, 045, 047, 0141, 0211
#~ b του ιησου 01
#~ c ιησου 05

#~ 22/60
#~ a συνεισηλθε A, P75, 02, 03, 05, 07, 011, 013, 017, 019, 021, 022, 028, 030, 031, 032, 034, 036, 037, 038, 044, 045, 047, 063, 091, 0141, 0211
#~ b συνεληλυθι 01

#~ 22/61
#~ a  A, P75, 01, 03, 05, 07, 011, 013, 017, 019, 021, 022, 028, 030, 031, 032, 034, 036, 037, 038, 044, 045, 047, 063, 091, 0141, 0211
#~ b ο ιησους 02

#~ 22/62-66
#~ b αυτοις A, 01
#~ a τοις μαθηταις αυτου P75, 02, 03, 05, 07, 011, 013, 017, 019, 021, 022, 028, 030, 031, 032, 034, 036, 037, 038, 044, 045, 047, 063, 091, 0141, 0211

#~ 22/68-70
#~ a ο ιησους A, P75, 01, 02, 03, 05, 07, 011, 013, 017, 019, 021, 022, 028, 030, 031, 032, 036, 037, 038, 044, 045, 047, 063, 091, 0141, 0211
#~ b  034

#~ 22/76
#~ a πλοιαριον 07, 011, 013, 021, 028, 030, 034, 036, 037, 038, 045, 047, 063
#~ b πλοιον P75, 01, 02, 03, 05, 017, 019, 022, 032, 044, 091, 0141, 0211

#~ 22/80
#~ a μονοι A, P75, 01, 02, 03, 07, 011, 013, 017, 019, 021, 022, 028, 030, 031, 032, 034, 036, 037, 038, 044, 045, 063, 091, 0141, 0211
#~ b μονον 05, 047

#~ 22/88
#~ a απηλθον P75, 02, 03, 05, 07, 011, 013, 017, 019, 021, 022, 028, 030, 032, 034, 036, 037, 044, 045, 047, 063, 091, 0141, 0211
#~ b εισηλθον 038
#~ c  01

#~ 23/1
#~ a  A, P75, 01, 02, 03, 05, 07, 011, 013, 017, 019, 021, 028, 030, 032, 034, 036, 037, 038, 044, 045, 047, 063, 091, 0141, 0211
#~ b και 022

#~ 23/2-10
#~ a αλλα ηλθεν πλοιαρια P75, 02, 03, 07, 011, 013, 017, 019, 021, 022, 028, 030, 031, 032, 034, 036, 037, 038, 044, 045, 047, 063, 091, 0141, 0211
#~ b επελθοντων ουν των πλοιων 01
#~ c αλλων πλοιαρειων ελθοντων 05

#~ 23/3
#~ a  A, P75, 03, 019, 091
#~ b δε 02, 07, 011, 013, 017, 021, 022, 028, 030, 032, 034, 036, 037, 038, 044, 045, 047, 063, 0141, 0211

#~ 23/4-10
#~ a ηλθεν πλοιαρια εκ τιβεριαδος 02, 07, 011, 013, 028, 030, 031, 034, 037, 038, 045, 063, 0211
#~ b ηλθεν πλοια εκ τιβεριαδος P75
#~ c ηλθεν πλοια εκ της τιβεριαδος 03, 032
#~ d ηλθον πλοιαρια εκ τιβεριαδος 021, 036, 047, 091
#~ e ηλθον πλοιαρια εκ της τιβεριαδος 022
#~ f πλοιαρια ηλθον εκ τιβεριαδος 017
#~ g πλοια ηλθεν εκ τιβεριαδος 044
#~ h πλοιαρια εκ τιβεριαδος ηλθον 019
#~ i πλοια εκ τιβεριαδος ηλθεν 0141

#~ 23/12-16
#~ a εγγυς του τοπου P75, 02, 03, 05, 07, 011, 013, 017, 019, 021, 022, 028, 030, 031, 034, 036, 037, 038, 044, 045, 047, 063, 091, 0141, 0211
#~ b εγγυς ουσης 01
#~ c  032

#~ 23/20-22
#~ a εφαγον τον P75, 02, 03, 05, 07, 011, 013, 017, 019, 021, 022, 028, 030, 031, 032, 034, 036, 037, 038, 044, 045, 047, 063, 091, 0141, 0211
#~ b και εφαγον 01

#~ 23/26-30
#~ a ευχαριστησαντος του κυριου P75, 01, 03, 07, 011, 013, 017, 019, 021, 022, 028, 030, 031, 032, 034, 036, 037, 038, 044, 045, 047, 063, 0141, 0211
#~ b ευχαριστησαντος του θεου 02
#~ c  05, 091

#~ 24/2-10
#~ a οτε ουν ειδεν ο οχλος P75, 02, 03, 05, 07, 011, 013, 017, 019, 021, 022, 028, 030, 031, 032, 034, 036, 037, 038, 044, 045, 047, 063, 091, 0141, 0211
#~ b και ιδοντες 01

#~ 24/6
#~ a ειδεν P75, 02, 03, 05, 07, 011, 017, 019, 021, 022, 028, 031, 032, 034, 036, 037, 038, 044, 045, 047, 063, 091, 0141, 0211
#~ b ειπεν 013
#~ c εγνω 030

#~ 24/14
#~ a ιησους A, P75, 02, 03, 05, 07, 011, 017, 019, 021, 022, 028, 030, 032, 034, 036, 037, 044, 045, 047, 091, 0141, 0211
#~ b ο ιησους 01, 038
#~ c  013

#~ 24/14-20
#~ a ο ιησους ουκ εστιν εκει P75, 02, 03, 05, 07, 011, 013, 017, 019, 021, 022, 028, 030, 032, 034, 036, 037, 038, 044, 045, 047, 063, 091, 0141, 0211
#~ b ουκ ην εκει ο ιησους 01

#~ 24/28
#~ a αυτου P75, 02, 03, 05, 07, 011, 013, 017, 019, 021, 022, 028, 030, 031, 032, 034, 036, 037, 038, 044, 045, 047, 0141, 0211
#~ b  01

#~ 24/30
#~ a ενεβησαν 02, 03, 07, 011, 013, 017, 021, 022, 028, 030, 031, 032, 034, 036, 037, 038, 044, 045, 047, 0141, 0211
#~ b ανεβησαν P75, 01, 019

#~ 24/30-32
#~ a ενεβησαν αυτοι P75, 01, 02, 03, 07, 011, 013, 017, 019, 021, 022, 028, 030, 031, 032, 034, 036, 037, 038, 044, 045, 047, 0141
#~ b τοτε και αυτοι ενεβησαν 0211

#~ 24/30-38
#~ a ενεβησαν αυτοι εις τα πλοια P75, 01, 02, 03, 07, 011, 013, 017, 019, 021, 022, 028, 030, 031, 032, 034, 036, 037, 038, 044, 045, 047, 0141, 0211
#~ b ελαβον εαυτοις πλοιαρια 05

#~ 24/31
#~ a  A, P75, 01, 02, 03, 07, 011, 013, 017, 019, 021, 022, 028, 031, 032, 034, 037, 038, 044, 045, 047, 0141
#~ b και 030, 036, 0211

#~ 24/32
#~ a αυτοι P75, 02, 03, 07, 011, 013, 017, 019, 021, 022, 030, 031, 032, 034, 036, 037, 038, 044, 045, 047, 0141, 0211
#~ c  01, 028

#~ 24/36
#~ a τα P75, 02, 03, 07, 011, 013, 017, 019, 021, 022, 028, 030, 031, 032, 034, 036, 037, 038, 044, 045, 047, 063, 0141, 0211
#~ b το 01

#~ 24/38
#~ a πλοια 02, 07, 011, 013, 017, 021, 028, 030, 031, 034, 036, 037, 038, 045, 047, 0141, 0211
#~ b πλοιαρια P75, 03, 05, 019, 022, 032, 044
#~ c πλοιον 01

#~ 24/50-52
#~ a τον ιησουν A, P75, 01, 02, 03, 05, 07, 011, 013, 019, 021, 022, 028, 030, 031, 032, 034, 036, 037, 038, 044, 045, 047, 063, 0141, 0211
#~ b αυτον 017

echo "All tests completed with good exit codes"