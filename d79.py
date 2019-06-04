#!/usr/bin/env python3

"""
Build a local SPARQL database.

Usage:
  d79 load_strains <db> <table_filename>
  d79 tag_strains <db> <idlist_filename> <tag>
  d79 tag_gb <db> <gblist_filename> <tag>
  d79 load_factor <db> <table_filename> <relation> [--key-type=<key>] 
  d79 serialize <db> <serial_filename>
  d79 add_gbids <db> <gb_list_filename>

Options:
  -h --help         Show this screen.
  --key-type <key>  The subject type to merge on [default="strain"].
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
  g.open(arguments["<db>"], create=True)

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

  if arguments["load_factor"]:
    recipe.load_factor(
      g,
      arguments["<table_filename>"],
      arguments["<relation>"],
      arguments["--key-type"]
    )

  if arguments["serialize"]:
    g.serialize(
      destination=arguments["<serial_filename>"],
      format="turtle",
      encoding="utf-8"
    )

  g.close()
