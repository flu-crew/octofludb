#!/usr/bin/env python3

"""
Build a local SPARQL database.

Usage:
  d79 load_strains <db_filename> <table_filename>
  d79 tag_strains <db_filename> <idlist_filename> <tag>
  d79 serialize <db_filename> <serial_filename>
  d79 add_gbids <db_filename> <gb_list_filename>

Options:
  -h --help     Show this screen.
"""

import sys
import os
from docopt import docopt
from rdflib import (ConjunctiveGraph)
from src.nomenclature import (uidgen)
import src.recipes as recipe
import src.entrez as entrez
import src.genbank as gb

if __name__ == '__main__':

  arguments = docopt(__doc__, version='build.sh 0.0.1')

  uid = uidgen()
  g = ConjunctiveGraph(store="Sleepycat")
  g.open(arguments["<db_filename>"], create=True)

  if arguments["load_strains"]:
    # load big table from IVR, with roughly the following format:
    # (gb | host | ? | subtype | date | ? | "Influenza A virus (<strain>(<subtype>))" | ...)
    recipe.load_influenza_na(g, arguments["<table_filename>"])

  if arguments["tag_strains"]:
    recipe.tag_strains(g, arguments["<idlist_filename>"], arguments["<tag>"])

  if arguments["add_gbids"]:
    with open(arguments["<gb_list_filename>"], "r") as f:
      gbids = [g.strip() for g in f.readlines()]
      for gb_meta in entrez.get_gbs(gbids):
        gb.add_gb_meta_triples(g, gb_meta)
    g.commit()

  if arguments["serialize"]:
    g.serialize(
      destination=arguments["<serial_filename>"],
      format="turtle",
      encoding="utf-8"
    )

  g.close()
