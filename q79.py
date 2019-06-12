#!/usr/bin/env python3

"""
Query the graph database with SPARQL files

If --as-fasta is used, the first (n-1) rows will be treated as '|'-separated
elements of the header. The nth row must contain raw sequence. The sequence
will all be on one line. If you want to wrap it, I suggest piping to `smof
clean`.

Usage:
  sparql.py <rdf_db> <sparql_query> [--as-fasta]

Options:
  -h --help     Show this screen.
  --as-fasta    Create a fasta file as output.
"""

from rdflib import ConjunctiveGraph
from rdflib.plugins.sparql import prepareQuery
from src.nomenclature import (nt)
from docopt import docopt
import sys
from rdflib.namespace import RDF, FOAF, XSD

def load_rdf(filename):
  with open(filename, "r") as f:
    sparql_str = f.read().strip()
  return(sparql_str)

if __name__ == '__main__':

  arguments = docopt(__doc__, version='sparql.sh 0.0.1')

  g = ConjunctiveGraph()
  g.parse(arguments["<rdf_db>"])

  if len(g) == 0:
    print("Loaded an empty database", file=sys.stderr)

  rdf_str = load_rdf(arguments["<sparql_query>"])

  qres = g.query(rdf_str, initNs = {"foaf":FOAF, "usda":nt, "xsd":XSD })

  # Set empty fields to "-". Empty fields occur when a SPARQL query uses OPTIONAL. 
  def to_str(x):
    if x == None:
      return "-"
    else:
      return str(x)

  if arguments["--as-fasta"]:
    for row in qres:
      seq = row[-1]
      header = '|'.join((to_str(x) for x in row[0:(len(row)-1)]))
      print(f'>{header}')
      print(seq)
  else:
    for row in qres:
      print('\t'.join((to_str(x) for x in row)))

  g.close()
