#!/usr/bin/env python3

"""
Build a local SPARQL database.

Usage:
  d79 load_strains <table_filename> [<db>]
  d79 tag <idlist_filename> <tag> [<db>]
  d79 load_excel <table_filename> [<db>] [--tag=<tag>]
  d79 load_gbids <gb_list_filename> [<db>]
  d79 load_blast <blast_filename> [<db>] [--tag=<tag>]
  d79 load_fasta <fasta_filename> [<db>] [--tag=<tag>] [--delimiter=<del>]

Options:
  -h --help               Show this screen.
  -k --key-type <key>     The subject type to merge on [default:"strain"]
  --delimiter <del>       Field delimiter for FASTA headers [default:"|"]
"""

import os
import sys
from docopt import docopt
from rdflib import Graph
import src.recipes as recipe
import src.entrez as entrez
import src.genbank as gb
import src.classes as classes
from src.nomenclature import manager
import signal
from tqdm import tqdm
from src.util import log

if __name__ == "__main__":

    if os.name is "posix":
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    args = docopt(__doc__, version="build.sh 0.0.1")

    g = Graph(namespace_manager=manager)

    if args["load_strains"]:
        # load big table from IVR, with roughly the following format:
        # (gb | host | ? | subtype | date | ? | "Influenza A virus (<strain>(<subtype>))" | ...)
        recipe.load_influenza_na(g, args["<table_filename>"])

    if args["tag"]:
        recipe.tag(g, args["<idlist_filename>"], args["<tag>"])

    if args["load_gbids"]:
        with open(args["<gb_list_filename>"], "r") as f:
            gbids = [g.strip() for g in f.readlines()]
            for gb_metas in entrez.get_gbs(gbids):
                for gb_meta in gb_metas:
                    gb.add_gb_meta_triples(g, gb_meta)
                # commit the current batch (say of 1000 entries)
                g.commit()

    if args["load_excel"]:
        classes.Table(args["<table_filename>"], tag=args["--tag"]).connect(g)

    if args["load_blast"]:
        recipe.load_blast(g, args["<blast_filename>"], tag=args["--tag"])

    if args["load_fasta"]:
        classes.Ragged(args["<fasta_filename>"], tag=args["--tag"]).connect(g)

    g.commit() # just in case we missed anything

    log("Serializing to turtle format ... ", end="")
    turtles = g.serialize(format="turtle")
    log("done")
    for l in turtles.splitlines():
        print(l.decode("utf-8"))

    g.close()
