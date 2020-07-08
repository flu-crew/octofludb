#!/usr/bin/env python3


"""
Build a local SPARQL database.

Usage:
  octofludb query [<sparql_filename>] [--header] [--fasta] [--url=<url>] [--repo=<repo>]
  octofludb upload [<turtle_filenames>...] [--url=<url>] [--repo=<repo>]
  octofludb mk_ivr [<filename>]
  octofludb mk_ird [<filename>]
  octofludb mk_gis [<filename>]
  octofludb tag [<filename>] [--tag=<tag>]
  octofludb mk_gbids [<filename>]
  octofludb mk_gbank [<filename>]
  octofludb mk_blast [<filename>] [--tag=<tag>]
  octofludb mk_table [<filename>] [--tag=<tag>] [--include=<inc>] [--exclude=<exc>] [--levels=<levels>] [--na=<na_str>]
  octofludb mk_fasta [<filename>] [--tag=<tag>] [--delimiter=<del>] [--include=<inc>] [--exclude=<exc>] [--na=<na_str>]

Options:
  -h --help               Show this screen.
  -k --key-type <key>     The subject type to merge on [default: "strain"]
  --delimiter <del>       Field delimiter for FASTA headers [default: "|"]
  --include <inc>         Only parse using these tokens (comma-delimited list) [default: ""]
  --exclude <exc>         Remove these tokens (comma-delimited list) [default: ""]
  --header                Include a header of column names indata returned from query
  --fasta                 Return query as a fasta file where last column is sequence
  --url <url>             GraphDB url [default: http://localhost:7200]
  --repo <repo>           GraphDB repo name [default: flu]
"""

import os
import signal
import pgraphdb as db
from docopt import docopt

if __name__ == "__main__":

    if os.name is "posix":
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    args = docopt(__doc__, version="octofludb 0.2.0")

    # Place imports here so they only load after successful parsing of the arguments.
    # If the imports are all before main, then `octofludb -h` can take a few seconds to run.
    import sys
    import shutil
    from Bio import SeqIO
    from rdflib import Graph, Literal
    import src.recipes as recipe
    import src.formatting as formatting
    import src.entrez as entrez
    import src.genbank as gb
    import src.classes as classes
    import datetime as datetime
    from src.nomenclature import manager, make_uri, make_tag_uri, P
    from tqdm import tqdm
    from src.util import log, file_str

    if args["query"]:
        results = db.sparql_query(
            sparql_file=args["<sparql_filename>"],
            url=args["--url"],
            repo_name=args["--repo"],
        )
        if args["--fasta"]:
            formatting.write_as_fasta(results)
        else:
            formatting.write_as_table(results, header=args["--header"])

        sys.exit(0)

    if args["upload"]:
        for filename in args["<turtle_filenames>"]:
            new_filename = os.path.join(
                os.path.expanduser("~"), "graphdb-import", os.path.basename(filename)
            )
            if filename == new_filename:
                continue
            else:
                try:
                    shutil.copyfile(filename, new_filename)
                except AttributeError as e:
                    print(
                        f"Could not move {filename} to {new_filename}: {str(e)}",
                        file=sys.stderr,
                    )
                    sys.exit(1)

        server_files = [os.path.basename(f) for f in args["<turtle_filenames>"]]

        db.load_data(
            url=args["--url"], repo_name=args["--repo"], turtle_files=server_files
        )
        sys.exit(0)

    tagstr = args["--tag"]

    if args["<filename>"]:
        filehandle = open(args["<filename>"], "r")
    else:
        filehandle = sys.stdin

    if args["--na"]:
        na_str = args["--na"].split(",")
        if isinstance(na_str, list):
            na_str = [None] + na_str
        else:
            na_str = [None, na_str]
    else:
        na_str = [None]

    g = Graph(namespace_manager=manager)

    if args["mk_ivr"]:
        # load big table from IVR, with roughly the following format:
        # (gb | host | ? | subtype | date | ? | "Influenza A virus (<strain>(<subtype>))" | ...)
        recipe.mk_influenza_na(g, filehandle)

    if args["mk_ird"]:
        recipe.mk_ird(g, filehandle)

    if args["mk_gis"]:
        recipe.mk_gis(g, filehandle)

    if args["tag"]:
        taguri = make_tag_uri(tagstr)
        g.add((taguri, P.name, Literal(tagstr)))
        g.add((taguri, P.time, Literal(datetime.datetime.now())))
        g.add((taguri, P.file, Literal(file_str(filehandle))))
        for identifier in (s.strip() for s in filehandle.readlines()):
            g.add((make_uri(identifier), P.tag, taguri))
        g.commit()

    if args["mk_gbids"]:
        log(f"Retrieving and parsing genbank ids from '{file_str(filehandle)}'")
        gbids = [g.strip() for g in filehandle.readlines()]
        for gb_metas in entrez.get_gbs(gbids):
            for gb_meta in gb_metas:
                gb.add_gb_meta_triples(g, gb_meta)
            # commit the current batch (say of 1000 entries)
            g.commit()

    if args["mk_gbank"]:
        print("mk_gbank is not yet supported", file=sys.stderr)
        sys.exit(1)
        #  for gb_meta in SeqIO.parse(filehandle, "genbank"):
        #      gb.add_gb_meta_triples(g, gb_meta)
        #  g.commit()

    if args["mk_blast"]:
        log(f"Retrieving and parsing blast results from '{file_str(filehandle)}'")
        recipe.mk_blast(g, filehandle, tag=tagstr)

    if args["mk_table"] or args["mk_fasta"]:
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

        if args["mk_table"]:
            classes.Table(
                filehandle=filehandle,
                tag=tagstr,
                include=inc,
                exclude=exc,
                log=True,
                na_str=na_str,
                levels=levels,
            ).connect(g)

        if args["mk_fasta"]:
            classes.Ragged(
                filehandle=filehandle,
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
