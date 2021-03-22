#!/usr/bin/env python3

import click
import collections
import os
import pgraphdb as db
import requests
import signal
import sys
import textwrap

import octofludb.cli as cli
from octofludb.util import log


def open_graph():
    from rdflib import Graph
    from octofludb.nomenclature import manager

    return Graph(namespace_manager=manager)


def with_graph(f, filename=None, outfile=sys.stdout, *args, **kwargs):
    g = open_graph()

    if filename is not None:
        with open(filename, "r") as fh:
            f(g, fh, *args, **kwargs)
    else:
        f(g, *args, **kwargs)

    g.commit()  # just in case we missed anything
    log("Serializing to turtle format ... ", end="")
    turtles = g.serialize(format="turtle")
    log("done")
    for l in turtles.splitlines():
        print(l.decode("utf-8"), file=outfile)
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


# Thanks to Максим Стукало from https://stackoverflow.com/questions/47972638
# for the solution to getting the subcommands to order non-alphabetically
class OrderedGroup(click.Group):
    def __init__(self, name=None, commands=None, **attrs):
        super(OrderedGroup, self).__init__(name, commands, **attrs)
        self.commands = commands or collections.OrderedDict()

    def list_commands(self, ctx):
        return self.commands


CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

url_opt = click.option("--url", help="GraphDB URL", default="http://localhost:7200")

filename_arg = click.argument("filename", type=click.Path(exists=True))

repo_name_opt = click.option("--repo", help="Repository name", default="octofludb")

tag_arg_pos = click.argument("tag")

tag_arg_opt = click.option(
    "--tag", help="A tag to associate with each identifier", type=str
)

segment_key_opt = click.option(
    "--segment-key", help="Treat the first column as a segment identifier. This is necessary for irregular segment identifiers (such as sequence checksums), for genbank or epiflu IDs, not special actio is needed, since octofludb will automatically recognize them.",
    is_flag=True, default=False
)

sparql_filename_pos = click.argument("sparql_filename", type=click.Path(exists=True))

all_the_turtles = click.argument(
    "turtle_filenames", type=click.Path(exists=True), nargs=-1
)

header_opt = click.option(
    "--header",
    is_flag=True,
    help="Include a header of column names indata returned from query",
)

fasta_opt = click.option(
    "--fasta",
    is_flag=True,
    help="Return query as a fasta file where last column is sequence",
)

delimiter_opt = click.option(
    "--delimiter", help="The delimiter between fields in the header", default="|"
)


@click.command(
    name="init",
)
@url_opt
@repo_name_opt
def init_cmd(url, repo):
    """
    Initialize an empty octofludb database
    """
    config_file = os.path.join(
        os.path.dirname(__file__), "data", "octofludb-config.ttl"
    )
    try:
        db.make_repo(config=config_file, url=url)
    except requests.exceptions.ConnectionError:
        print(f"Could not connect to a GraphDB database at {args.url}", file=sys.stderr)
        sys.exit(1)


@click.command(
    name="clean",
)
@url_opt
@repo_name_opt
def clean_cmd(url, repo):
    """
    clean the database (not yet implemented)
    """
    raise NotImplemented


@click.command(
    name="query",
)
@sparql_filename_pos
@header_opt
@fasta_opt
@url_opt
@repo_name_opt
def query_cmd(sparql_filename, header, fasta, url, repo):
    """
    Submit a SPARQL query to octofludb
    """
    import octofludb.formatting as formatting

    results = db.sparql_query(sparql_file=sparql_filename, url=url, repo_name=repo)
    if fasta:
        formatting.write_as_fasta(results)
    else:
        formatting.write_as_table(results, header=header)
    sys.exit(0)


@click.command(
    name="update",
)
@sparql_filename_pos
@url_opt
@repo_name_opt
def update_cmd(sparql_filename, url, repo):
    """
    Submit a SPARQL delete or insert query to octofludb
    """
    db.update(sparql_file=sparql_filename, url=url, repo_name=repo)
    return None


@click.command(
    name="upload",
)
@all_the_turtles
@url_opt
@repo_name_opt
def upload_cmd(turtle_filenames, url, repo):
    """
    Upload one or more turtle files to the database
    """
    import shutil

    for filename in turtle_filenames:
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
    server_files = [os.path.basename(f) for f in turtle_filenames]
    db.load_data(url=url, repo_name=repo, turtle_files=server_files)
    sys.exit(0)


# ===== prep subcommands ====


@click.command(
    name="tag",
)
@click.argument("tag", type=str)
@filename_arg
def prep_tag_cmd(tag, filename):
    """
    Associate list of IDs with a tag
    """
    from rdflib import Literal
    import datetime as datetime
    from octofludb.nomenclature import make_uri, make_tag_uri, P
    from octofludb.util import file_str

    g = open_graph()
    with open(filename, "r") as fh:
        taguri = make_tag_uri(tag)
        g = open_graph()
        g.add((taguri, P.name, Literal(tag)))
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


@click.command(
    name="ivr",
)
@filename_arg
def prep_ivr_cmd(filename):
    """
    Translate an IVR table to RDF.

    load big table from IVR, with roughly the following format:
    gb | host | - | subtype | date | - | "Influenza A virus (<strain>(<subtype>))" | ...
    """
    import octofludb.recipes as recipe

    with_graph(recipe.mk_influenza_na, filename)


@click.command(
    name="ird",
)
@filename_arg
def prep_ird_cmd(filename):
    """
    Translate an IRD table to RDF.
    """

    with_graph(recipe.mk_ird, filename)


@click.command(
    name="gis",
)
@filename_arg
def prep_gis_cmd(filename):
    """
    Translate a Gisaid metadata excel file to RDF.
    
    "filename" is a path to a Gisaid metadata excel file
    """
    import octofludb.recipes as recipe

    with_graph(recipe.mk_gis, filename)


def _mk_gbids_cmd(g, gbids=[]):
    import octofludb.entrez as entrez
    import octofludb.genbank as gb

    for gb_metas in entrez.get_gbs(gbids):
        for gb_meta in gb_metas:
            gb.add_gb_meta_triples(g, gb_meta)
        # commit the current batch (say of 1000 entries)
        g.commit()


@click.command(
    name="gbids",
)
@filename_arg
def prep_gbids_cmd(*args, **kwargs):
    """
    Retrieve data for a list of genbank ids.

    <filename> contains a list of genbank ids
    """
    with open(filename, "r") as fh:
        gbids = [gbid.strip() for gbid in fh]
    log(f"Retrieving and parsing genbank ids from '{args.filename}'")
    with_graph(_mk_gbids_cmd, gbids=gbids)


@click.command(name="update_gb")
@click.option(
    "--minyear",
    help="Earliest year to update",
    default=1918,
    type=click.IntRange(
        min=1900, max=3021
    ),  # yes, octofludb will be used for a thousand years
)
@click.option(
    "--maxyear",
    help="Latest year to update",
    default=3021,
    type=click.IntRange(min=1900, max=3021),
)
@click.option(
    "--nmonths",
    help="Update Genbank files for the last N months",
    default=1440,
    type=click.IntRange(min=1, max=9999),
)
def prep_update_gb_cmd(minyear, maxyear, nmonths):
    """
    Retrieve any missing genbank records. Results are stored in files with the prefix '.gb_###.ttl'
    """
    from octofludb.entrez import missing_acc_by_date
    import octofludb.colors as colors

    for date, missing_acc in missing_acc_by_date(
        min_year=minyear, max_year=maxyear, nmonths=nmonths
    ):
        if missing_acc:
            log(colors.good(f"Updating {date} ..."))
            outfile = ".gb_" + date.replace("/", "-") + ".ttl"
            with open(outfile, "w") as fh:
                with_graph(_mk_gbids_cmd, gbids=missing_acc, outfile=fh)
        else:
            log(colors.good(f"Up-to-date for {date}"))


@click.command(
    name="blast",
)
@tag_arg_opt
@filename_arg
def prep_blast_cmd(tag, filename):
    """
    Translate BLAST results into RDF.

    <filename> File containing a list of genbank ids
    """
    import octofludb.recipes as recipe

    log(f"Retrieving and parsing blast results from '{filename}'")
    with_graph(recipe.mk_blast, filename, tag=tag)


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


include_opt = click.option(
    "--include", help="Only parse using these tokens (comma-delimited list)", default=""
)
exclude_opt = click.option(
    "--exclude", help="Remove these tokens (comma-delimited list)", default=""
)
na_opt = click.option("--na", help="The string that represents a missing value")


@click.command(
    name="table",
)
@filename_arg
@tag_arg_opt
@include_opt
@exclude_opt
@click.option("--levels", help="levels")
@na_opt
@segment_key_opt
def prep_table_cmd(filename, tag, include, exclude, levels, na, segment_key):
    """
    Translate a table to RDF
    """
    from octofludb.classes import Table
    from octofludb.recipes import IrregularSegmentTable;

    if segment_key:
        constructor = IrregularSegmentTable
    else:
        constructor = Table

    def _mk_table_cmd(g, fh):
        (inc, exc, levelsProc) = process_tablelike(include, exclude, levels)
        constructor(
            filehandle=fh,
            tag=tag,
            include=inc,
            exclude=exc,
            log=True,
            levels=levelsProc,
            na_str=make_na(na),
        ).connect(g)

    with_graph(_mk_table_cmd, filename)

@click.command(
    name="fasta",
)
@filename_arg
@tag_arg_opt
@delimiter_opt
@include_opt
@exclude_opt
@na_opt
def prep_fasta_cmd(filename, tag, delimiter, include, exclude, na):
    """
    Translate a fasta file to RDF.

    <filename> Path to a TAB-delimited or excel table
    """
    import octofludb.classes as classes

    def _mk_fasta_cmd(g, fh):
        (inc, exc, levels) = process_tablelike(include, exclude, None)
        classes.Ragged(
            filehandle=fh,
            tag=tag,
            include=inc,
            exclude=exc,
            log=True,
            levels=levels,
            na_str=make_na(na),
        ).connect(g)

    with_graph(_mk_fasta_cmd, filename)


@click.command(
    name="unpublished",
)
@filename_arg
@tag_arg_opt
@delimiter_opt
@include_opt
@exclude_opt
@na_opt
def prep_unpublished_cmd(filename, tag, delimiter, include, exclude, na):
    """
    Prepare an unpublished set up sequences.

    The input is a fasta file where the header is a series of terms separated
    by a delimiter ("|" by default).
    
    The first term MUST be the strain ID. This can be anything. For example,
    "A/swine/12345678/2020' or some arbitrary id.  If the ID is used elsewhere
    in the database to refer to a strain, then all data loaded here will be
    assumed to describe the other ID as well (i.e., they are considered to be
    the same thing).

    The sequence is assumed to be a segment of unknown subtype and clade. It
    will be associated with the strain by its MD5 checksum. Subtype/clade info
    can be added through octoFLU.

    Additional terms after the strain ID may be added. Any term that looks like
    a date (e.g., "2020-12-31") will be parsed as the collection date. Country
    names like "United States" or 3-letter country codes (e.g., USA or CAN) are
    supported.

    I strongly recommend you skim the output turtle file before uploading to
    the database.

    The "unpublished" tag is automatically associated with the segments in
    addition to any tag specified through the `--tag` option.
    """
    import octofludb.recipes as recipe

    def _mk_unpublisehd_fasta_cmd(g, fh):
        (inc, exc, levels) = process_tablelike(include, exclude, None)
        recipe.IrregularFasta(
            filehandle=fh,
            tag=tag,
            include=inc,
            exclude=exc,
            log=True,
            levels=levels,
            na_str=make_na(na),
        ).connect(g)

    with_graph(_mk_unpublisehd_fasta_cmd, filename)


@click.group(
    cls=OrderedGroup,
    name="prep",
    context_settings=CONTEXT_SETTINGS,
)
def prep_grp():
    """
    Various recipes for prepping data for uploading.
    """
    pass


prep_grp.add_command(prep_update_gb_cmd)
prep_grp.add_command(prep_fasta_cmd)
prep_grp.add_command(prep_table_cmd)
prep_grp.add_command(prep_unpublished_cmd)
prep_grp.add_command(prep_tag_cmd)
prep_grp.add_command(prep_blast_cmd)
prep_grp.add_command(prep_gbids_cmd)
prep_grp.add_command(prep_gis_cmd)
prep_grp.add_command(prep_ird_cmd)
prep_grp.add_command(prep_ivr_cmd)


# ===== make subcommands ====


@click.command(
    name="const",
)
@url_opt
@repo_name_opt
def make_const_cmd(url, repo):
    """
    Generate constellations for all swine strains.

    A constellation is a succinct description of the internal 6 genes. The
    description consists of 6 symbols representing the phylogenetic clades of
    the 6 proteins: PB2, PB1, PA, NP, M, and NS. Current US strains should
    consist of genes from 3 groups: pandemic (P), TRIG (T), and the LAIV
    vaccine strain (V). "-" indicates that no sequence is available for the
    given segment. "H" represents a human seasonal internal gene (there are
    only a few of these in the US. "X" represents something else exotic (e.g.,
    not US). For mixed strains, the constellation will be recorded as "mixed".
    """
    import octofludb.formatting as formatting

    sparql_filename = os.path.join(os.path.dirname(__file__), "data", "segments.rq")
    results = db.sparql_query(
        sparql_file=sparql_filename, url=url, repo_name=repo
    )
    formatting.write_constellations(results)


@click.command(
    name="subtypes",
)
@url_opt
@repo_name_opt
def make_subtypes_cmd(url, repo):
    """
    Determine subtypes based on Genbank serotype field, epiflu data, or octoflu HA/NA classifications"
    """
    import octofludb.recipes as recipe

    sparql_filename = os.path.join(os.path.dirname(__file__), "data", "subtypes.rq")

    results = db.sparql_query(
        sparql_file=sparql_filename, url=url, repo_name=repo
    )

    recipe.mk_subtypes(results)


@click.command(
    name="masterlist",
)
@url_opt
@repo_name_opt
def make_masterlist_cmd(url, repo):
    """
    Generate the surveillance masterlist
    """
    import octofludb.recipes as recipe

    sparql_filename = os.path.join(os.path.dirname(__file__), "data", "masterlist.rq")

    results = db.sparql_query(
        sparql_file=sparql_filename, url=url, repo_name=repo
    )

    recipe.mk_masterlist(results)


@click.command(
    name="motifs",
)
@url_opt
@repo_name_opt
def make_motifs_cmd(url, repo):
    """
    Generate motifs for H1 and H3
    """
    raise NotImplemented


@click.group(
    cls=OrderedGroup,
    name="make",
    context_settings=CONTEXT_SETTINGS,
)
def make_grp():
    """
    Derive constellations, subtypes, motifs and such
    """
    pass


make_grp.add_command(make_const_cmd)
make_grp.add_command(make_subtypes_cmd)
make_grp.add_command(make_masterlist_cmd)
make_grp.add_command(make_motifs_cmd)


# ===== fetch subcommands =====

@click.command(
    name="tag",
)
@url_opt
@repo_name_opt
def fetch_tag_cmd(url, repo):
    """
    Upload list of tags
    """
    raise NotImplemented

@click.command(
    name="isolate",
)
@url_opt
@repo_name_opt
def fetch_isolate_cmd(url, repo):
    """
    Fetch tagged isolate data
    """
    raise NotImplemented

@click.command(
    name="strain",
)
@url_opt
@repo_name_opt
def fetch_strain_cmd(url, repo):
    """
    Fetch tagged strain data
    """
    raise NotImplemented

@click.command(
    name="segment",
)
@url_opt
@repo_name_opt
def fetch_segment_cmd(url, repo):
    """
    Fetch tagged segment data
    """
    raise NotImplemented

@click.command(
    name="clear",
)
@url_opt
@repo_name_opt
def fetch_clear_cmd(url, repo):
    """
    Clear all uploaded tags
    """
    raise NotImplemented

@click.group(
    cls=OrderedGroup,
    name="fetch",
    context_settings=CONTEXT_SETTINGS,
)
def fetch_grp():
    """
    Tag and fetch data

    Use the "tag" subcommand to push lists of identifiers (as either a
    comma-delimited string or a file with one identifier per line).

    These identifiers will all be tagged for retrieval in the database.

    They may be fetched with the "isolate", "strain" or "segment" commands
    (dependeing on what is tagged).

    Tags can be cleared with `clear`. Until cleared, the tags reside in the
    database, allowing multiple retrievals or allowing other database
    operations to interact with the tagged sets (not a recommended operation).
    """
    pass

fetch_grp.add_command(fetch_tag_cmd)
fetch_grp.add_command(fetch_isolate_cmd)
fetch_grp.add_command(fetch_strain_cmd)
fetch_grp.add_command(fetch_segment_cmd)
fetch_grp.add_command(fetch_clear_cmd)


# ===== report subcommands =====


@click.command(
    name="monthly",
)
@url_opt
@repo_name_opt
def report_monthly_cmd(url, repo):
    """
    Surveillance data for the given month (basis of WGS selections)
    """
    raise NotImplemented


@click.command(
    name="quarter",
)
@url_opt
@repo_name_opt
def report_quarter_cmd(url, repo):
    """
    Surveillance data for the quarter (basis of quarterly reports)
    """
    raise NotImplemented


@click.command(
    name="offlu",
)
@url_opt
@repo_name_opt
def report_offlu_cmd(url, repo):
    """
    Synthesize public and private data needed for offlu reports
    """
    raise NotImplemented


@click.group(
    cls=OrderedGroup,
    name="report",
    context_settings=CONTEXT_SETTINGS,
)
def report_grp():
    """
    Build standardized reports from the data
    """
    pass


report_grp.add_command(report_monthly_cmd)
report_grp.add_command(report_quarter_cmd)
report_grp.add_command(report_offlu_cmd)


# ===== deletion subcommands =====


@click.command(
    name="constellations",
)
@url_opt
@repo_name_opt
def delete_constellations_cmd(url, repo):
    """
    Delete all constellation data
    """
    raise NotImplemented


@click.command(
    name="subtypes",
)
@url_opt
@repo_name_opt
def delete_subtypes_cmd(url, repo):
    """
    Delete all subtype data
    """
    raise NotImplemented


@click.command(
    name="clades",
)
@url_opt
@repo_name_opt
def delete_clades_cmd(url, repo):
    """
    Delete all clade data
    """
    raise NotImplemented


@click.command(
    name="gl_clades",
)
@url_opt
@repo_name_opt
def delete_gl_clades_cmd(url, repo):
    """
    Delete all global H1 clade data
    """
    raise NotImplemented


@click.group(
    cls=OrderedGroup,
    name="delete",
    context_settings=CONTEXT_SETTINGS,
)
def delete_grp():
    """
    Remove data from the database in various ways
    """
    pass


delete_grp.add_command(delete_constellations_cmd)
delete_grp.add_command(delete_subtypes_cmd)
delete_grp.add_command(delete_clades_cmd)
delete_grp.add_command(delete_gl_clades_cmd)


@click.group(cls=OrderedGroup, context_settings=CONTEXT_SETTINGS)
def cli_grp():
    """
    API and utilities for the USDA swine IVA surveillance database
    """
    pass


cli_grp.add_command(init_cmd)
cli_grp.add_command(clean_cmd)
cli_grp.add_command(query_cmd)
cli_grp.add_command(update_cmd)
cli_grp.add_command(upload_cmd)
cli_grp.add_command(prep_grp)
cli_grp.add_command(make_grp)
cli_grp.add_command(fetch_grp)
cli_grp.add_command(report_grp)
cli_grp.add_command(delete_grp)


def main():
    cli_grp()


if __name__ == "__main__":
    if os.name is "posix":
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    main()
