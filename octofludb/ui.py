#!/usr/bin/env python3

import os
import sys
import signal
import pgraphdb as db
import argparse
import textwrap
import requests
import octofludb.cli as cli


parser = argparse.ArgumentParser(
    prog="octofludb",
    formatter_class=cli.SubcommandHelpFormatter,
    description="API and utilities for the swine flu surveillance database",
    epilog=textwrap.dedent(
        "Submit issue reports to https://github.com/flu-crew/octofludb/issues"
    ),
)
subparsers = parser.add_subparsers(metavar="<subcommand>", title="subcommands")
subcommand = cli.subcommand_maker(subparsers)

url_arg = cli.argument("--url", help="GraphDB URL", default="http://localhost:7200")
repo_name_arg = cli.argument("--repo", help="Repository name", default="octofludb")
tag_arg_pos = cli.argument("tag", help="A tag to associate with each identifier")
tag_arg_opt = cli.argument("--tag", help="A tag to associate with each identifier")


def open_graph():
    from rdflib import Graph
    from octofludb.nomenclature import manager

    return Graph(namespace_manager=manager)


def with_graph(f, filename, *args, **kwargs):
    from octofludb.util import log

    g = open_graph()
    with open(filename, "r") as fh:
        f(g, fh, *args, **kwargs)
        g.commit()  # just in case we missed anything
        log("Serializing to turtle format ... ", end="")
        turtles = g.serialize(format="turtle")
        log("done")
        for l in turtles.splitlines():
            print(l.decode("utf-8"))
    g.close()


def open_file(path):
    if path:
        filehandle = open(args["<filename>"], "r")
    else:
        filehandle = sys.stdin
    return filehandle


def make_na(na_str):
    if na_str:
        na_list = na_str.split(",")
        if isinstance(na_list, list):
            na_list = [None] + na_str
        else:
            na_list = [None, na_list]
    else:
        na_list = [None]
    return na_list


@subcommand(["init", url_arg, repo_name_arg])
def call_init_cmd(args):
    """
    Initialize an empty octofludb database
    """
    config_file = os.path.join(
        os.path.dirname(__file__), "data", "octofludb-config.ttl"
    )
    try:
        db.make_repo(config=config_file, url=args.url)
    except requests.exceptions.ConnectionError:
        print(f"Could not connect to a GraphDB database at {args.url}", file=sys.stderr)
        sys.exit(1)


@subcommand(
    [
        "query",
        cli.argument("sparql_filename"),
        cli.argument(
            "--header",
            help="Include a header of column names indata returned from query",
            action="store_true",
            default=False,
        ),
        cli.argument(
            "--fasta",
            help="Return query as a fasta file where last column is sequence",
            action="store_true",
            default=False,
        ),
        url_arg,
        repo_name_arg,
    ]
)
def call_query_cmd(args):
    """
    Submit a SPARQL query to octofludb
    """
    import octofludb.formatting as formatting

    results = db.sparql_query(
        sparql_file=args.sparql_filename, url=args.url, repo_name=args.repo
    )
    if args.fasta:
        formatting.write_as_fasta(results)
    else:
        formatting.write_as_table(results, header=args.header)
    sys.exit(0)


@subcommand(["update", cli.argument("sparql_filename"), url_arg, repo_name_arg])
def call_query_cmd(args):
    """
    Submit a SPARQL delete or insert query to octofludb
    """
    db.update(sparql_file=args.sparql_filename, url=args.url, repo_name=args.repo)
    return None


@subcommand(
    [
        "upload",
        cli.argument(
            "turtle_filenames", help="One or more turtle filenames", nargs="+"
        ),
        url_arg,
        repo_name_arg,
    ]
)
def call_upload_cmd(args):
    """
    Upload one or more turtle files to the database
    """
    import shutil

    for filename in args.turtle_filenames:
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

    server_files = [os.path.basename(f) for f in args.turtle_filenames]

    db.load_data(url=args.url, repo_name=args.repo, turtle_files=server_files)
    sys.exit(0)


@subcommand(["tag", cli.argument("filename", help="File of identifiers"), tag_arg_pos])
def tag_cmd(args):
    """
    Associate list of IDs with a tag
    """
    from rdflib import Literal
    import datetime as datetime
    from octofludb.nomenclature import make_uri, make_tag_uri, P
    from octofludb.util import file_str

    from octofludb.util import log

    g = open_graph()
    with open(args.filename, "r") as fh:
        taguri = make_tag_uri(args.tag)
        g = open_graph()
        g.add((taguri, P.name, Literal(args.tag)))
        g.add((taguri, P.time, Literal(datetime.datetime.now())))
        g.add((taguri, P.file, Literal(file_str(fh))))
        for identifier in (s.strip() for s in fh.readlines()):
            g.add((make_uri(identifier), P.tag, taguri))
        g.commit()  # just in case we missed anything
        log("Serializing to turtle format ... ", end="")
        turtles = g.serialize(format="turtle")
        log("done")
        for l in turtles.splitlines():
            print(l.decode("utf-8"))
    g.close()


@subcommand(["mk_ivr", cli.argument("filename", help="The filename of an IVR table")])
def mk_ivr_cmd(args):
    """
    Translate an IVR table to RDF

    load big table from IVR, with roughly the following format:
    gb | host | - | subtype | date | - | "Influenza A virus (<strain>(<subtype>))" | ...
    """
    import octofludb.recipes as recipe

    with_graph(recipe.mk_influenza_na, args.filename)


@subcommand(["mk_ird", cli.argument("filename", help="The filename of an IRD table")])
def mk_ivr_cmd(args):
    """
    Translate an IRD table to RDF
    """
    import octofludb.recipes as recipe

    with_graph(recipe.mk_ird, args.filename)


@subcommand(
    ["mk_gis", cli.argument("filename", help="Path to a Gisaid metadata excel file")]
)
def mk_gis_cmd(args):
    """
    Translate a Gisaid metadata excel file to RDF
    """
    import octofludb.recipes as recipe

    with_graph(recipe.mk_gis, args.filename)


@subcommand(
    ["mk_gbids", cli.argument("filename", help="File containing a list of genbank ids")]
)
def mk_gbids_cmd(args):
    """
    Retrieve data for a list of genbank ids
    """
    import octofludb.entrez as entrez
    import octofludb.genbank as gb
    from octofludb.util import log, file_str

    def _mk_gbids_cmd(g, fh):
        log(f"Retrieving and parsing genbank ids from '{file_str(fh)}'")
        gbids = [gbid.strip() for gbid in fh.readlines()]
        for gb_metas in entrez.get_gbs(gbids):
            for gb_meta in gb_metas:
                gb.add_gb_meta_triples(g, gb_meta)
            # commit the current batch (say of 1000 entries)
            g.commit()

    with_graph(_mk_gbids_cmd, args.filename)


@subcommand(
    [
        "mk_blast",
        cli.argument("filename", help="File containing a list of genbank ids"),
        tag_arg_opt,
    ]
)
def mk_blast_cmd(args):
    """
    Translate BLAST results into RDF
    """
    import octofludb.recipes as recipe
    from octofludb.util import log, file_str

    log(f"Retrieving and parsing blast results from '{args.filename}'")
    with_graph(recipe.mk_blast, args.filename, tag=args.tag)


def process_tablelike(include, exclude, levels):
    if not include:
        inc = {}
    else:
        inc = set(include.split(","))
    if not exclude:
        exc = {}
    else:
        exc = set(exclude.split(","))
    if not levels:
        levels = None
    else:
        levels = {s.strip() for s in levels.split(",")}
    return (inc, exc, levels)


include_arg = cli.argument(
    "--include", help="Only parse using these tokens (comma-delimited list)", default=""
)
exclude_arg = cli.argument(
    "--exclude", help="Remove these tokens (comma-delimited list)", default=""
)
na_arg = cli.argument("--na", help="The string that represents a missing value")


@subcommand(
    [
        "mk_table",
        cli.argument("filename", help="Path to a table"),
        tag_arg_opt,
        include_arg,
        exclude_arg,
        cli.argument("--levels", help="levels"),
        na_arg,
    ]
)
def mk_table_cmd(args):
    """
    Translate a table to RDF
    """
    import octofludb.classes as classes

    def _mk_table_cmd(g, fh):
        (inc, exc, levels) = process_tablelike(args.include, args.exclude, args.levels)
        classes.Table(
            filehandle=fh,
            tag=args.tag,
            include=inc,
            exclude=exc,
            log=True,
            levels=levels,
            na_str=make_na(args.na),
        ).connect(g)

    with_graph(_mk_table_cmd, args.filename)


@subcommand(
    [
        "mk_fasta",
        cli.argument("filename", help="Path to a TAB-delimited or excel table"),
        tag_arg_opt,
        cli.argument(
            "--delimiter",
            help="The delimiter between fields in the header",
            default="|",
        ),
        include_arg,
        exclude_arg,
        na_arg,
    ]
)
def mk_fasta_cmd(args):
    """
    Translate a fasta file to RDF
    """
    import octofludb.classes as classes

    def _mk_fasta_cmd(g, fh):
        (inc, exc, levels) = process_tablelike(args.include, args.exclude, None)
        classes.Ragged(
            filehandle=fh,
            tag=args.tag,
            include=inc,
            exclude=exc,
            log=True,
            levels=levels,
            na_str=make_na(args.na),
        ).connect(g)

    with_graph(_mk_fasta_cmd, args.filename)


def main():
    args = parser.parse_args()
    if len(vars(args)) == 0:
        parser.print_help()
    else:
        args.func(args)


if __name__ == "__main__":
    if os.name is "posix":
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    main()
