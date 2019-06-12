#!/usr/bin/env python3

"""
Build a local SPARQL database.

Usage:
  d79 load_strains <table_filename> [<db>] [--rdf=<rdf>] [--format=<format>]
  d79 tag_strains <idlist_filename> <tag> [<db>]  [--rdf=<rdf>] [--format=<format>]
  d79 tag_gb <gblist_filename> <tag> [<db>]  [--rdf=<rdf>] [--format=<format>]
  d79 load_factor <table_filename> <relation> <db> [--key-type=<key>]  [--rdf=<rdf>] [--format=<format>]
  d79 load_excel <table_filename> [<db>] [--event=<event>] [--rdf=<rdf>] [--format=<format>]
  d79 load_gbids <gb_list_filename> [<db>] [--rdf=<rdf>] [--format=<format>]
  d79 load_blast <blast_filename> [<db>] [--event=<event>] [--rdf=<rdf>] [--format=<format>]
  d79 serialize <serial_filename> <db> [--format=<format>]

Options:
  -h --help             Show this screen.
  -k --key-type <key>   The subject type to merge on [default="strain"].
  -f --format <format>  The RDF format ("turtle" or "ntriples")
"""

import sys
import os
from docopt import docopt
from rdflib import (ConjunctiveGraph)
import src.recipes as recipe
import src.entrez as entrez
import src.genbank as gb

if __name__ == '__main__':

  arguments = docopt(__doc__, version='build.sh 0.0.1')

  if arguments["<db>"]:
    g = ConjunctiveGraph(store="Sleepycat")
    g.open(arguments["<db>"], create=True)
  else:
    g = ConjunctiveGraph()

  if arguments["load_strains"]:
    # load big table from IVR, with roughly the following format:
    # (gb | host | ? | subtype | date | ? | "Influenza A virus (<strain>(<subtype>))" | ...)
    recipe.load_influenza_na(g, arguments["<table_filename>"])

  if arguments["tag_strains"]:
    recipe.tag_strains(g, arguments["<idlist_filename>"], arguments["<tag>"])

  if arguments["load_gbids"]:
    with open(arguments["<gb_list_filename>"], "r") as f:
      gbids = [g.strip() for g in f.readlines()]
      for gb_metas in entrez.get_gbs(gbids):
        for gb_meta in gb_metas:
          gb.add_gb_meta_triples(g, gb_meta)
        # commit the current batch (say of 1000 entries)
        g.commit()
        print(f' > uploaded and committed {len(gb_metas)} ids', file=sys.stderr)

  if arguments["load_excel"]:
    recipe.load_excel(g, arguments["<table_filename>"], event=arguments["--event"])

  if arguments["load_blast"]:
    recipe.load_blast(g, arguments["<blast_filename>"], event=arguments["--event"])

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
      format=arguments["--format"],
      encoding="utf-8"
    )

  if arguments["--rdf"]:
    g.serialize(
      destination=arguments["--rdf"],
      format=arguments["--format"],
      encoding="utf-8"
    )

  g.close()
