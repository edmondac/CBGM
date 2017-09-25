#!/usr/bin/env python3
# Analyse a CSV combination of ancestors file, to find the best combination


import csv


def log(msg, *args):
    print(" > {}".format(msg % args))


class Analyser(object):
    def __init__(self, csv_file):
        """
        Load the file, and do simple elimination of unwanted rows
        """
        with open(csv_file) as f:
            r = csv.DictReader(f)
            self.has_hinweis = False
            self.min_offen = 1000000
            rows = []
            for row in r:
                rows.append(row)
                self.min_offen = min(self.min_offen, int(row['Offen']))
                if not self.has_hinweis:
                    if row['Hinweis'] == '<<':
                        self.has_hinweis = True
                        log("Found Hinweis '<<' entries")

        log("Loaded %s rows", len(rows))

        if self.has_hinweis:
            log("Restricting search to Hinweis '<<' rows")
            self.best_rows = [x for x in rows if x['Hinweis'] == '<<']
        else:
            self.best_rows = rows

        log("Min 'Offen' is %s", self.min_offen)
        self.best_rows = [x for x in self.best_rows if int(x['Offen']) == self.min_offen]
        log('%s rows have Offen=%s', len(self.best_rows), self.min_offen)

    def analyse(self, max_by_posterity=10):
        """
        Search for the best row
        """
        # Get best of each size
        best_by_size = {}
        for row in self.best_rows:
            existing = best_by_size.get(row['Vorfanz'])
            if not existing:
                # Don't already have one of this size
                best_by_size[row['Vorfanz']] = row
                continue
            if row['Post'] < existing['Post']:
                # This one explains fewer by posterity
                best_by_size[row['Vorfanz']] = row
                continue
            if row['Post'] == existing['Post'] and row['sum_rank'] < existing['sum_rank']:
                # This one has lower sum_rank, while explaining the same number by posterity
                best_by_size[row['Vorfanz']] = row
                continue

        log("Restricted to the best of each combination size: %s combinations left", len(best_by_size))

        # Find combinations that are as good but with fewer members
        best_by_post = {}
        for row in best_by_size.values():
            existing = best_by_post.get(int(row['Post']))
            if not existing:
                best_by_post[int(row['Post'])] = row
                continue
            if row['Vorfanz'] < existing['Vorfanz']:
                best_by_post[int(row['Post'])] = row
                continue

        log("Excluded rows with more combinations but no better results: %s combinations left", len(best_by_post))

        if len(best_by_post) == 1:
            log("Only one combination left: %s", best_by_post.values()[0]['Vorf'])

        else:
            log("Human thought required...")
            last_row = None
            best_post = min(best_by_post.keys())

            for k in sorted(best_by_post.keys()):
                row = best_by_post[k]
                if best_post + max_by_posterity < k:
                    # That's too many to consider by posterity - abort
                    break

                if last_row:
                    my_post_vus = set([x.strip() for x in row['vus_post'].split(',')])
                    his_post_vus = set([x.strip() for x in last_row['vus_post'].split(',')])
                    log("Combination {%s} explains the following by posterity (compared to {%s}): %s",
                        row['Vorf'], last_row['Vorf'], my_post_vus - his_post_vus)
                    if not his_post_vus.issubset(my_post_vus):
                        log("... and the other way round: %s", his_post_vus - my_post_vus)
                else:
                    log("Combination {%s} explains the most by agreement", row['Vorf'])

                last_row = row


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Helper script to analyse combination of ancestors CSV file.")
    parser.add_argument('csv_file', help="Input CSV file")
    parser.add_argument('-p', '--post-limit', type=int, default=10,
                        help=("Maximum number of extra variant units to consider by posterity"))
    args = parser.parse_args()
    Analyser(args.csv_file).analyse(args.post_limit)
