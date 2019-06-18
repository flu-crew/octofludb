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
  d79 load_fasta <fasta_filename> [<db>] [--event=<event>] [--rdf=<rdf>] [--format=<format>] [--columns=<columns>] [--delimiter=<del>]
  d79 serialize <serial_filename> <db> [--format=<format>]

Options:
  -h --help               Show this screen.
  -k --key-type <key>     The subject type to merge on [default="strain"].
  -f --format <format>    The RDF format ("turtle" or "ntriples")
  -c --columns <columns>  Columns of a table for fields in a header (e.g., "sid[host,date,gid],gid[clade],host,date,clade|(sid,type,strain_id);(gid,type,barcode);(gid,type,genbank_id)"
"""

import sys
import os
from docopt import docopt
from rdflib import (ConjunctiveGraph)
import src.recipes as recipe
import src.entrez as entrez
import src.genbank as gb

if __name__ == '__main__':

  args = docopt(__doc__, version='build.sh 0.0.1')

  if args["<db>"]:
    g = ConjunctiveGraph(store="Sleepycat")
    g.open(args["<db>"], create=True)
  else:
    g = ConjunctiveGraph()

  if args["load_strains"]:
    # load big table from IVR, with roughly the following format:
    # (gb | host | ? | subtype | date | ? | "Influenza A virus (<strain>(<subtype>))" | ...)
    recipe.load_influenza_na(g, args["<table_filename>"])

  if args["tag_strains"]:
    recipe.tag_strains(g, args["<idlist_filename>"], args["<tag>"])

  if args["load_gbids"]:
    with open(args["<gb_list_filename>"], "r") as f:
      gbids = [g.strip() for g in f.readlines()]
      for gb_metas in entrez.get_gbs(gbids):
        for gb_meta in gb_metas:
          gb.add_gb_meta_triples(g, gb_meta)
        # commit the current batch (say of 1000 entries)
        g.commit()
        print(f' > uploaded and committed {len(gb_metas)} ids', file=sys.stderr)

  if args["load_excel"]:
    recipe.load_excel(g, args["<table_filename>"], event=args["--event"])

  if args["load_blast"]:
    recipe.load_blast(g, args["<blast_filename>"], event=args["--event"])

  if args["load_fasta"]:
    recipe.load_fasta(g, args["<fasta_filename>"], event=args["--event"], columns=args["--columns"], delimiter=args["--delimiter"])

  if args["load_factor"]:
    recipe.load_factor(
      g,
      args["<table_filename>"],
      args["<relation>"],
      args["--key-type"]
    )

  if args["serialize"]:
    g.serialize(
      destination=args["<serial_filename>"],
      format=args["--format"],
      encoding="utf-8"
    )

  if args["--rdf"]:
    g.serialize(
      destination=args["--rdf"],
      format=args["--format"],
      encoding="utf-8"
    )

  g.close()
