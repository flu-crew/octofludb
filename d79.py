#!/usr/bin/env python3

"""
Build a local SPARQL database.

Usage:
  d79 load_strains [<filename>]
  d79 tag [<filename>] [--tag=<tag>]
  d79 load_gbids [<filename>]
  d79 load_blast [<filename>] [--tag=<tag>]
  d79 load_excel [<filename>] [--tag=<tag>] [--include=<inc>] [--exclude=<exc>]
  d79 load_fasta [<filename>] [--tag=<tag>] [--delimiter=<del>] [--include=<inc>] [--exclude=<exc>]

Options:
  -h --help               Show this screen.
  -k --key-type <key>     The subject type to merge on [default:"strain"]
  --delimiter <del>       Field delimiter for FASTA headers [default:"|"]
  --include <inc>         Only parse using these tokens (comma-delimited list) [default:""]
  --exclude <exc>         Remove these tokens (comma-delimited list) [default:""]
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
from src.util import log, file_str

if __name__ == "__main__":

    if os.name is "posix":
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    args = docopt(__doc__, version="build.sh 0.0.1")
    tagstr = args["--tag"]

    if args["<filename>"]:
        filehandle = open(args["<filename>"], "r")
    else:
        filehandle = sys.stdin

    g = Graph(namespace_manager=manager)

    if args["load_strains"]:
        # load big table from IVR, with roughly the following format:
        # (gb | host | ? | subtype | date | ? | "Influenza A virus (<strain>(<subtype>))" | ...)
        recipe.load_influenza_na(g, filehandle)

    if args["tag"]:
        for identifier in (s.strip() for s in filehandle.readlines()):
            g.add((make_uri(identifier), P.tag, Literal(tagstr)))
        g.commit()

    if args["load_gbids"]:
        log(f"Retrieving and parsing genbank ids from '{file_str(filehandle)}'")
        gbids = [g.strip() for g in filehandle.readlines()]
        for gb_metas in entrez.get_gbs(gbids):
            for gb_meta in gb_metas:
                gb.add_gb_meta_triples(g, gb_meta)
            # commit the current batch (say of 1000 entries)
            g.commit()

    if args["load_blast"]:
        log(f"Retrieving and parsing blast results from '{file_str(filehandle)}'")
        recipe.load_blast(g, filehandle, tag=tagstr)

    if args["load_excel"] or args["load_fasta"]:
        if not args["--include"]:
            inc = {}
        else:
            inc = set(args["--include"].split(","))
        if not args["--exclude"]:
            exc = {}
        else:
            exc = set(args["--exclude"].split(","))

        if args["load_excel"]:
            classes.Table(
                filehandle,
                tag=tagstr,
                include=inc,
                exclude=exc,
                log=True,
            ).connect(g)

        if args["load_fasta"]:
            classes.Ragged(
                filehandle,
                tag=tagstr,
                include=inc,
                exclude=exc,
                log=True,
            ).connect(g)

    g.commit() # just in case we missed anything

    log("Serializing to turtle format ... ", end="")
    turtles = g.serialize(format="turtle")
    log("done")
    for l in turtles.splitlines():
        print(l.decode("utf-8"))

    filehandle.close()
    g.close()
