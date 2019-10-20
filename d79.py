#!/usr/bin/env python3

"""
Build a local SPARQL database.

Usage:
  d79 load_ivr [<filename>]
  d79 load_ird [<filename>]
  d79 load_gis [<filename>]
  d79 tag [<filename>] [--tag=<tag>]
  d79 load_gbids [<filename>]
  d79 load_gbank [<filename>]
  d79 load_blast [<filename>] [--tag=<tag>]
  d79 load_table [<filename>] [--tag=<tag>] [--include=<inc>] [--exclude=<exc>] [--levels=<levels>] [--na=<na_str>]
  d79 load_fasta [<filename>] [--tag=<tag>] [--delimiter=<del>] [--include=<inc>] [--exclude=<exc>] [--na=<na_str>]

Options:
  -h --help               Show this screen.
  -k --key-type <key>     The subject type to merge on [default:"strain"]
  --delimiter <del>       Field delimiter for FASTA headers [default:"|"]
  --include <inc>         Only parse using these tokens (comma-delimited list) [default:""]
  --exclude <exc>         Remove these tokens (comma-delimited list) [default:""]
"""

import os
import signal
from docopt import docopt

if __name__ == "__main__":

    if os.name is "posix":
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    args = docopt(__doc__, version="build.sh 0.0.1")
    tagstr = args["--tag"]

    # Place imports here so they only load after successful parsing of the arguments.
    # If the imports are all before main, then `d79 -h` can take a few seconds to run. 
    import sys
    from Bio import SeqIO
    from rdflib import Graph, Literal
    import src.recipes as recipe
    import src.entrez as entrez
    import src.genbank as gb
    import src.classes as classes
    import datetime as datetime
    from src.nomenclature import manager, make_uri, make_tag_uri, P
    from tqdm import tqdm
    from src.util import log, file_str

    if args["<filename>"]:
        filehandle = open(args["<filename>"], "r")
    else:
        filehandle = sys.stdin

    if args["--na"]:
        na_str = args["--na"].split(",")
        if (isinstance(na_str, list)):
            na_str = [None] + na_str
        else:
            na_str = [None, na_str]
    else:
        na_str = [None]

    g = Graph(namespace_manager=manager)

    if args["load_ivr"]:
        # load big table from IVR, with roughly the following format:
        # (gb | host | ? | subtype | date | ? | "Influenza A virus (<strain>(<subtype>))" | ...)
        recipe.load_influenza_na(g, filehandle)

    if args["load_ird"]:
        recipe.load_ird(g, filehandle)

    if args["load_gis"]:
        recipe.load_gis(g, filehandle)

    if args["tag"]:
        taguri = make_tag_uri(tagstr)
        g.add((taguri, P.name, Literal(tagstr)))
        g.add((taguri, P.time, Literal(datetime.datetime.now())))
        g.add((taguri, P.file, Literal(file_str(filehandle))))
        for identifier in (s.strip() for s in filehandle.readlines()):
            g.add((make_uri(identifier), P.tag, taguri))
        g.commit()

    if args["load_gbids"]:
        log(f"Retrieving and parsing genbank ids from '{file_str(filehandle)}'")
        gbids = [g.strip() for g in filehandle.readlines()]
        for gb_metas in entrez.get_gbs(gbids):
            for gb_meta in gb_metas:
                gb.add_gb_meta_triples(g, gb_meta)
            # commit the current batch (say of 1000 entries)
            g.commit()

    if args["load_gbank"]:
        print("load_gbank is not yet supported", file=sys.stderr)
        sys.exit(1)
        #  for gb_meta in SeqIO.parse(filehandle, "genbank"):
        #      gb.add_gb_meta_triples(g, gb_meta)
        #  g.commit()

    if args["load_blast"]:
        log(f"Retrieving and parsing blast results from '{file_str(filehandle)}'")
        recipe.load_blast(g, filehandle, tag=tagstr)

    if args["load_table"] or args["load_fasta"]:
        if not args["--include"]:
            inc = {}
        else:
            inc = set(args["--include"].split(","))
        if not args["--exclude"]:
            exc = {}
        else:
            exc = set(args["--exclude"].split(","))
        if not args["--levels"]:
            levels = None
        else:
            levels = {s.strip() for s in args["--levels"].split(",")}

        if args["load_table"]:
            classes.Table(
                filehandle=filehandle,
                tag=tagstr,
                include=inc,
                exclude=exc,
                log=True,
                na_str=na_str,
                levels=levels,
            ).connect(g)

        if args["load_fasta"]:
            classes.Ragged(
                filehandle,
                tag=tagstr,
                include=inc,
                exclude=exc,
                log=True,
                levels=levels,
                na_str=na_str,
            ).connect(g)

    g.commit()  # just in case we missed anything

    log("Serializing to turtle format ... ", end="")
    turtles = g.serialize(format="turtle")
    log("done")
    for l in turtles.splitlines():
        print(l.decode("utf-8"))

    filehandle.close()
    g.close()
