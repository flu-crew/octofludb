#!/usr/bin/env python3

"""
Query the graph database with SPARQL files

Usage:
  q79.py <sparql_query> [--repo=<repo>] [--header] [--fasta]

Options:
  -h --help     Show this screen.
  --repo <repo> GraphDB repo name
  --header      Print a header
  --fasta       Write fasta, where last variable is assumed to be the sequence
"""

from SPARQLWrapper import SPARQLWrapper, JSON
from docopt import docopt

if __name__ == "__main__":

    args = docopt(__doc__, version="sparql.sh 0.0.1")

    if args["--repo"]:
        repo = args["--repo"]
    else:
        repo = "flu"

    with open(args["<sparql_query>"], "r") as fh:
        sparql_file = fh.read()

    sparql = SPARQLWrapper(f'http://localhost:7200/repositories/{repo}')
    sparql.setQuery(sparql_file)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    if args["--fasta"]:
        header_fields = results["head"]["vars"][:-1]
        seq_field = results["head"]["vars"][-1]
        for row in results["results"]["bindings"]:
            header = "|".join(row[field]["value"] for field in header_fields)
            sequence = row[seq_field]["value"]
            print(">" + header)
            print(sequence)
    else:
        if args["--header"]:
            print("\t".join(results["head"]["vars"]))
        for row in results["results"]["bindings"]:
            fields = (row[field]["value"] for field in results["head"]["vars"])
            print("\t".join(fields))
