from __future__ import annotations
from typing import TextIO, NoReturn, Optional, List, Set, Tuple

import click
import collections
import sys
import os
from rdflib import Graph
from rdflib.term import Node
from octofludb.util import log, safeAdd
from octofludb.version import __version__


def open_graph() -> Graph:
    from octofludb.nomenclature import manager

    return Graph(namespace_manager=manager)


def with_graph(
    triples: Set[Tuple[Node, Node, Node]], outfile: TextIO = sys.stdout
) -> None:
    g = open_graph()

    # Add the new triples
    for triple in triples:
        g.add(triple)

    # Commit them to the database (memory, in this case)
    g.commit()

    log("Serializing to turtle format ... ", end="")
    turtles = g.serialize(format="turtle")
    log("done")
    for line in turtles.splitlines():
        print(line, file=outfile)
    g.close()

    return None


def make_na(na_str: Optional[str]) -> List[str]:
    """
    Process a string holding comma separated options for NAs

    It may be None, if no NA was specified. It may be an empty string, if an
    empty string was specified. This is a meaningful option since "" is a
    perfectly normal NA value.

    None will always be added as an option.
    """

    if na_str is None:
        na_list = []
    else:
        # This will return a non-empty list. Either multiple strings or a
        # single empty string, since `"".split(",") == ['']`
        na_list = na_str.split(",")

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

filehandle_r_arg = click.argument("filename", type=click.File("r"))

repo_name_opt = click.option("--repo", help="Repository name", default="octofludb")

tag_arg_pos = click.argument("tag")

tag_arg_opt = click.option(
    "--tag", help="A tag to associate with each identifier", type=str
)

segment_key_opt = click.option(
    "--segment-key",
    help="Treat the first column as a segment identifier. This is necessary for irregular segment identifiers (such as sequence checksums), for genbank or epiflu IDs, not special actio is needed, since octofludb will automatically recognize them.",
    is_flag=True,
    default=False,
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
def init_cmd(url: str, repo: str) -> NoReturn:
    """
    Initialize an empty octofludb database
    """
    import pgraphdb as db
    import requests
    import octofludb.script as script

    config_file = os.path.join(
        os.path.dirname(__file__), "data", "octofludb-config.ttl"
    )
    try:
        db.make_repo(config=config_file, url=url)
    except requests.exceptions.ConnectionError:
        print(f"Could not connect to a GraphDB database at {url}", file=sys.stderr)
        sys.exit(1)

    octofludb_home = os.path.join(os.path.expanduser("~"), ".octofludb")

    if not os.path.exists(octofludb_home):
        try:
            print(
                f" - Creating local configuration folder at '{octofludb_home}'",
                file=sys.stderr,
            )
            os.mkdir(octofludb_home)
        except FileExistsError:
            print(
                f" Failed to create {octofludb_home}",
                file=sys.stderr,
            )
            sys.exit(1)

    script.initialize_config_file()

    sys.exit(0)


def upload_gisaid(config: dict, url: str, repo: str) -> List[str]:
    import octofludb.script as script
    import octofludb.recipes as recipe

    uploaded_files = []

    epiflu_metafiles = script.epiflu_meta_files(config)
    skipped_meta = 0
    if epiflu_metafiles:
        for epiflu_metafile in epiflu_metafiles:
            outfile = os.path.basename(epiflu_metafile) + ".ttl"
            if os.path.exists(outfile) and os.path.getsize(outfile) > 0:
                skipped_meta += 1
            else:
                with open(outfile, "w") as fo:
                    with_graph(recipe.mk_gis(epiflu_metafile), outfile=fo)
                uploaded_files += upload([outfile], url=url, repo=repo)
    else:
        log("No epiflu metafiles found")
    if skipped_meta > 0:
        log(
            f"Skipped {str(skipped_meta)} epiflu meta files where existing non-empty turtle files were found in the build directory"
        )

    epiflu_fastafiles = script.epiflu_fasta_files(config)
    skipped_fasta = 0
    if epiflu_fastafiles:
        for infile in epiflu_fastafiles:
            outfile = os.path.basename(infile) + ".ttl"
            if os.path.exists(outfile) and os.path.getsize(outfile) > 0:
                skipped_fasta += 1
            else:
                with open(outfile, "w") as f:
                    prep_fasta(filename=infile, outfile=f)
                    uploaded_files += upload([outfile], url=url, repo=repo)
    else:
        log("No epiflu fasta found")

    if skipped_fasta > 0:
        log(
            f"Skipped {str(skipped_fasta)} epiflu fasta files where existing non-empty turtle files were found in the build directory"
        )

    return uploaded_files


def upload_classifications(url: str, repo: str) -> List[str]:
    import octofludb.script as script
    import pgraphdb as db

    # octoflu classifications of unclassified swine
    # * retrieve unclassified strains
    unclassified_fasta = "unclassified-swine.fna"
    unclassified_classes = "unclassified-swine.txt"
    unclassified_turtle = "unclassified-swine.ttl"

    sparql_file = script.get_data_file("fetch-unclassified-swine.rq")
    with open(unclassified_fasta, "w") as fastaout:
        fmt_query_cmd(
            sparql_filename=sparql_file,
            header=False,
            fasta=True,
            url=url,
            repo=repo,
            outfile=fastaout,
        )

    with open(unclassified_classes, "w") as classout:
        # feed them into runOctoFLU
        classify_and_write(unclassified_fasta, outfile=classout)

    with open(unclassified_turtle, "w") as turtleout:
        # print the results
        prep_table(unclassified_classes, outfile=turtleout)

    uploaded_unclassified = upload([unclassified_turtle], url=url, repo=repo)

    # infer constellations
    constellation_table = "constellations.txt"
    constellation_turtles = "constellations.ttl"

    delete_constellations = script.get_data_file("delete-constellations.rq")
    db.update(sparql_file=delete_constellations, url=url, repo_name=repo)

    with open(constellation_table, "w") as constout:
        make_const(url=url, repo=repo, outfile=constout)

    with open(constellation_turtles, "w") as turtleout:
        prep_table(constellation_table, outfile=turtleout)

    uploaded_constellations = upload([constellation_turtles], url=url, repo=repo)

    return uploaded_unclassified + uploaded_constellations


def upload_subtypes(url: str, repo: str) -> List[str]:

    # infer subtypes
    subtypes_table = "subtypes.txt"
    with open(subtypes_table, "w") as subtypesout:
        make_subtypes(url=url, repo=repo, outfile=subtypesout)

    # The subtype table needs to be split into genbank and epiflu tables to
    # ensure proper inference of strain name versus isolate id types.
    genbank_subtypes = "subtypes-genbank.txt"
    epiflu_subtypes = "subtypes-epiflu.txt"
    with open(subtypes_table, "r") as subtypesin:
        with open(genbank_subtypes, "w") as gh:
            print("strain_name\tsubtype", file=gh)
            with open(epiflu_subtypes, "w") as eh:
                print("isolate_id\tsubtype", file=eh)
                # the subtypes.txt file has a header which needs to be skipped
                for row in subtypesin.read().splitlines()[1:]:
                    if "EPI_ISL" in row:
                        print(row, file=eh)
                    else:
                        print(row, file=gh)
                eh.flush()
            gh.flush()

    gturtles = "subtypes-genbank.ttl"
    eturtles = "subtypes-epiflu.ttl"
    with open(gturtles, "w") as gturtleout:
        prep_table(filename=genbank_subtypes, outfile=gturtleout, segment_key="strain_name")
    with open(eturtles, "w") as eturtleout:
        prep_table(filename=epiflu_subtypes, outfile=eturtleout, segment_key="isolate_id")

    return upload([gturtles, eturtles], url=url, repo=repo)


def upload_motifs(url: str, repo: str) -> List[str]:
    import octofludb.script as script

    # find h1 motifs
    h1_motif_table = script.findMotifs(
        os.path.join(os.path.dirname(__file__), "data", "get-h1-swine.rq"),
        [
            "sa_motif=124,125,155,157,159,160,162,163,164",
            "sb_motif=153,156,189,190,193,195",
            "ca1_motif=166,170,204,237",
            "ca2_motif=137,140,142,221,222",
            "cb_motif=70,71,73,74,75,115",
        ],
        "H1",
        url=url,
        repo_name=repo,
    )

    with open("h1-motifs.ttl", "w") as turtleout:
        prep_table(h1_motif_table, outfile=turtleout)
    upload(["h1-motifs.ttl"], url=url, repo=repo)

    # find h3 motifs
    h3_motif_table = script.findMotifs(
        os.path.join(os.path.dirname(__file__), "data", "get-h3-swine.rq"),
        ["h3_motif=145,155,156,158,189"],
        "H3",
        url=url,
        repo_name=repo,
    )

    with open("h3-motifs.ttl", "w") as turtleout:
        prep_table(h3_motif_table, outfile=turtleout)

    return upload(["h3-motifs.ttl"], url=url, repo=repo)


@click.command(
    name="pull",
)
@click.option(
    "--nmonths",
    help="Update Genbank files for the last N months",
    default=1,
    type=click.IntRange(min=0, max=9999),
)
@click.option(
    "--no-schema", is_flag=True, default=False, help="Skip upload schema steps"
)
@click.option(
    "--no-clades",
    is_flag=True,
    default=False,
    help="Skip clade and constellation classification steps",
)
@click.option(
    "--no-subtype",
    is_flag=True,
    default=False,
    help="Skip subtype inferrence step",
)
@click.option(
    "--no-motifs", is_flag=True, default=False, help="Skip motif extraction steps"
)
@click.option(
    "--include-gisaid", is_flag=True, default=False, help="include gisaid data step"
)
@click.option(
    "--include-tags",
    is_flag=True,
    default=False,
    help="Upload tags as defined in the config file",
)
@url_opt
@repo_name_opt
def pull_cmd(
    nmonths: int,
    no_schema: bool,
    no_clades: bool,
    no_subtype: bool,
    no_motifs: bool,
    include_gisaid: bool,
    include_tags: bool,
    url: str,
    repo: str,
) -> NoReturn:
    """
    Update data. Pull from genbank, process any new data in the data folder,
    assign clades to swine data, assign subtypes to all data, and extract
    motifs.

    To build the database from nothing call `octofludb pull --nmonths=360`.
    This will pull all genbank data that has been released in the last 30
    years (which should be all of it).
    """
    import octofludb.script as script

    cwd = os.getcwd()

    script.gotoBuildHome()

    config = script.load_config_file()

    if not no_schema:
        # upload ontological schema
        schema_file = script.get_data_file("schema.ttl")  #
        upload([schema_file], url=url, repo=repo)

        # upload geological relationships
        upload([script.get_data_file("geography.ttl")], url=url, repo=repo)[0]

    if nmonths > 0:
        # update genbank (take a parameter telling how far back to go)
        # this command fills the current directory with .gb* files
        gb_turtles = prep_update_gb(minyear=1900, maxyear=2121, nmonths=nmonths)
        upload(gb_turtles, url=url, repo=repo)

    if include_gisaid:
        upload_gisaid(config, url, repo)

    if not no_clades:
        upload_classifications(url, repo)

    if not no_subtype:
        upload_subtypes(url, repo)

    if not no_motifs:
        upload_motifs(url, repo)

    if include_tags:
        # load all tags
        for (tag, basename) in config["tags"].items():
            for filename in script.tag_files(config, tag):
                outfile = filename + ".ttl"
                with open(outfile, "w") as f:
                    prep_tag(tag, filename, outfile=f)
                upload([outfile], url=url, repo=repo)

    os.chdir(cwd)

    sys.exit(0)


def fmt_query_cmd(
    sparql_filename: str,
    header: bool,
    fasta: bool,
    url: str,
    repo: str,
    outfile: TextIO = sys.stdout,
) -> TextIO:
    import octofludb.formatting as formatting
    import pgraphdb as db

    results = db.sparql_query(
        sparql_file=sparql_filename, url=url, repo_name=repo
    ).convert()
    if fasta:
        formatting.write_as_fasta(results, outfile=outfile)
    else:
        formatting.write_as_table(results, header=header, outfile=outfile)

    return outfile


@click.command(
    name="query",
)
@sparql_filename_pos
@header_opt
@fasta_opt
@url_opt
@repo_name_opt
def query_cmd(*args, **kwargs):
    """
    Submit a SPARQL query to octofludb
    """
    fmt_query_cmd(*args, **kwargs)


@click.command(name="classify")
@filename_arg
@click.option("--reference", help="An octoFLU reference fasta file", default=None)
def classify_cmd(filename: str, reference: Optional[str] = None) -> NoReturn:
    """
    Classify the sequences in a fasta file using octoFLU

    The reference file used will be selected as follows:

      1. If --reference=REFERENCE is given, use REFERENCE. If the file does not exist, die.

      2. If the term `octoflu_references` is defined in the `config.yaml` file
         in octoflu home, then use this file. If term is not null and does not
         exist, die.

      3. If no references are given, use the default reference in the octoFLU repo.
    """
    classify_and_write(filename, reference=None, outfile=sys.stdout)

    sys.exit(0)


def classify_and_write(
    filename: str, reference: Optional[str] = None, outfile: TextIO = sys.stdout
) -> None:
    rows = classify(filename, reference=reference)
    print("seqid\tsegment_subtype\tclade\tgl_clade", file=outfile)

    # This may be empty, that is fine. A table with only a heade line would
    # generate an empty turtle file. Uploading an empty turtle file does
    # nothing.
    for row in rows:
        print("\t".join(row), file=outfile)


def classify(filename: str, reference: Optional[str] = None) -> List[List[str]]:
    import octofludb.script as script

    if not reference:
        config = script.load_config_file()
        reference = script.get_octoflu_reference(config)
    return script.runOctoFLU(filename, reference)


@click.command(
    name="construct",
)
@sparql_filename_pos
@url_opt
@repo_name_opt
def construct_cmd(sparql_filename: str, url: str, repo: str) -> NoReturn:
    """
    Construct new triples
    """
    import pgraphdb as db

    results = db.sparql_construct(
        sparql_file=sparql_filename, url=url, repo_name=repo
    ).convert()

    print(results)

    sys.exit(0)


@click.command(
    name="update",
)
@sparql_filename_pos
@url_opt
@repo_name_opt
def update_cmd(sparql_filename: str, url: str, repo: str) -> NoReturn:
    """
    Submit a SPARQL delete or insert query to octofludb
    """
    import pgraphdb as db

    db.update(sparql_file=sparql_filename, url=url, repo_name=repo)

    sys.exit(0)


@click.command(
    name="upload",
)
@all_the_turtles
@url_opt
@repo_name_opt
def upload_cmd(turtle_filenames: List[str], url: str, repo: str) -> NoReturn:
    """
    Upload one or more turtle files to the database
    """
    upload(turtle_filenames, url, repo)

    sys.exit(0)


def upload(turtle_filenames: List[str], url: str, repo: str) -> List[str]:
    import pgraphdb as db
    import octofludb.script as script

    files = []
    for filenames in turtle_filenames:
        for filename in script.expandpath(filenames):
            log(f"loading file: {filename}")
            db.load_data(url=url, repo_name=repo, turtle_file=filename)
            files.append(filename)
    return files


# ===== prep subcommands ====


@click.command(
    name="tag",
)
@click.argument("tag", type=str)
@filename_arg
def prep_tag_cmd(tag: str, filename: str) -> NoReturn:
    """
    Associate list of IDs with a tag
    """
    prep_tag(tag, filename)

    sys.exit(0)


def prep_tag(tag: str, filename: str, outfile: TextIO = sys.stdout) -> None:
    import datetime as datetime
    from octofludb.nomenclature import make_uri, make_tag_uri, make_literal, P
    from octofludb.util import file_str

    with open(filename, "r") as fh:
        taguri = make_tag_uri(tag)
        g: Set[Tuple[Node, Node, Node]] = set()
        safeAdd(g, taguri, P.name, make_literal(tag, infer=False))
        safeAdd(g, taguri, P.time, make_literal(datetime.datetime.now()))
        safeAdd(g, taguri, P.file, make_literal(file_str(fh), infer=False))
        for identifier in (s.strip() for s in fh.readlines()):
            safeAdd(g, make_uri(identifier), P.tag, taguri)

        turtles = open_graph().update(g).commit().serialize(format="turtle")

        for line in turtles.splitlines():
            print(line, file=outfile)

    return None


@click.command(
    name="ivr",
)
@filehandle_r_arg
def prep_ivr_cmd(filename: TextIO) -> NoReturn:
    """
    Translate an IVR table to RDF.

    load big table from IVR, with roughly the following format:
    gb | host | - | subtype | date | - | "Influenza A virus (<strain>(<subtype>))" | ...
    """
    import octofludb.recipes as recipe

    with_graph(recipe.mk_influenza_na(filename))

    sys.exit(0)


@click.command(
    name="ird",
)
@filehandle_r_arg
def prep_ird_cmd(filename: TextIO) -> NoReturn:
    """
    Translate an IRD table to RDF.
    """

    import octofludb.recipes as recipe

    with_graph(recipe.mk_ird(filename))

    sys.exit(0)


@click.command(
    name="gis",
)
@filename_arg
def prep_gis_cmd(filename: str) -> NoReturn:
    """
    Translate a Gisaid metadata excel file to RDF.

    "filename" is a path to a Gisaid metadata excel file
    """
    import octofludb.recipes as recipe

    with_graph(recipe.mk_gis(filename=filename))

    sys.exit(0)


def _mk_gbids_cmd(gbids: List[str] = []) -> Set[Tuple[Node, Node, Node]]:
    import octofludb.entrez as entrez
    import octofludb.genbank as gb
    import octofludb.script as script

    error_msgs = []

    all_triples = set()

    for gb_metas in entrez.get_gbs(gbids):
        for gb_meta in gb_metas:
            (triples, error_msg) = gb.make_gb_meta_triples(gb_meta)
            if error_msg:
                error_msgs.append(error_msg)
            # commit the current batch (say of 1000 entries)
            all_triples.update(triples)

    if len(error_msgs) > 0:
        logpath = script.error_log_entry(error_msgs, "failed_genbank_parses.txt")
        log(f"{len(error_msgs)} genbank entries could not be parsed, see {logpath}")

    return all_triples


@click.command(
    name="gbids",
)
@filename_arg
def prep_gbids_cmd(filename: str) -> NoReturn:
    """
    Retrieve data for a list of genbank ids.

    <filename> contains a list of genbank ids
    """
    with open(filename, "r") as fh:
        gbids = [gbid.strip() for gbid in fh]
    log("Retrieving and parsing genbank ids from 'filename'")
    with_graph(_mk_gbids_cmd(gbids=gbids))

    sys.exit(0)


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
def prep_update_gb_cmd(minyear: int, maxyear: int, nmonths: int) -> NoReturn:
    """
    Retrieve any missing genbank records. Results are stored in files with the prefix '.gb_###.ttl'
    """
    prep_update_gb(minyear, maxyear, nmonths)

    sys.exit(0)


def prep_update_gb(minyear: int, maxyear: int, nmonths: int) -> List[str]:
    from octofludb.entrez import missing_acc_by_date
    import octofludb.colors as colors

    outfiles = []

    for date, missing_acc in missing_acc_by_date(
        min_year=minyear, max_year=maxyear, nmonths=nmonths
    ):
        if missing_acc:
            outfile = ".gb_" + date.replace("/", "-") + ".ttl"
            if os.path.exists(outfile) and os.path.getsize(outfile) > 0:
                log(f"GenBank turtle file for '{str(date)}' already exists, skipping")
            else:
                log(colors.good(f"Updating {date} ..."))
                with open(outfile, "w") as fh:
                    with_graph(_mk_gbids_cmd(gbids=missing_acc), outfile=fh)
                outfiles.append(outfile)
        else:
            log(colors.good(f"Up-to-date for {date}"))

    return outfiles


@click.command(
    name="blast",
)
@tag_arg_opt
@filehandle_r_arg
def prep_blast_cmd(tag: str, filename: TextIO) -> NoReturn:
    """
    Translate BLAST results into RDF.

    <filename> File containing a list of genbank ids
    """
    import octofludb.recipes as recipe

    log(f"Retrieving and parsing blast results from '{filename}'")
    with_graph(recipe.mk_blast(filename, tag=tag))

    sys.exit(0)


def process_tablelike(
    include: Optional[str], exclude: Optional[str], levels: Optional[str]
) -> Tuple[Set[str], Set[str], Optional[Set[str]]]:
    if include is None or include == "":
        inc = set()
    else:
        inc = set(include.split(","))

    if exclude is None or exclude == "":
        exc = set()
    else:
        exc = set(exclude.split(","))

    lev: Optional[Set[str]]
    if levels == "":
        lev = set()
    elif levels is None:
        lev = None
    else:
        lev = {s.strip() for s in levels.split(",")}

    return (inc, exc, lev)


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
def prep_table_cmd(*args, **kwargs):
    """
    Translate a table to RDF
    """
    prep_table(*args, **kwargs)


def prep_table(
    filename: str,
    tag: Optional[str] = None,
    include: Optional[str] = None,
    exclude: Optional[str] = None,
    levels: Optional[str] = None,
    na: Optional[str] = None,
    segment_key: Optional[str] = None,
    outfile: TextIO = sys.stdout,
) -> None:
    """
    Translate a table to RDF
    """
    from octofludb.recipes import IrregularSegmentTable
    import octofludb.classes as classes

    (inc, exc, levelsProc) = process_tablelike(include, exclude, levels)

    def _mk_table_cmd(fh: TextIO) -> Set[Tuple[Node, Node, Node]]:
        if segment_key is None:
            return IrregularSegmentTable(
                text=fh,
                tag=tag,
                include=inc,
                exclude=exc,
                log=True,
                levels=levelsProc,
                na_str=make_na(na),
            ).connect()
        else:
            return classes.Table(
                text=fh,
                tag=tag,
                include=inc,
                exclude=exc,
                log=True,
                levels=levelsProc,
                na_str=make_na(na),
            ).connect()

    with open(filename, "r") as fi:
        return with_graph(_mk_table_cmd(fi), outfile=outfile)


@click.command(
    name="fasta",
)
@filename_arg
@tag_arg_opt
@delimiter_opt
@include_opt
@exclude_opt
@na_opt
def prep_fasta_cmd(*args, **kwargs) -> NoReturn:
    """
    Translate a fasta file to RDF.

    <filename> Path to a TAB-delimited or excel table
    """

    prep_fasta(*args, **kwargs)

    sys.exit(0)


def prep_fasta(
    filename: str,
    tag: Optional[str] = None,
    delimiter: Optional[str] = None,
    include: Optional[str] = None,
    exclude: Optional[str] = None,
    na: Optional[str] = None,
    outfile: TextIO = sys.stdout,
) -> None:
    import octofludb.classes as classes

    def _mk_fasta_cmd(fh: TextIO) -> Set[Tuple[Node, Node, Node]]:
        (inc, exc, levels) = process_tablelike(include, exclude, None)
        return classes.Ragged(
            text=fh,
            tag=tag,
            include=inc,
            exclude=exc,
            log=True,
            levels=levels,
            na_str=make_na(na),
        ).connect()

    with open(filename, "r") as fasta_fh:
        with_graph(_mk_fasta_cmd(fasta_fh), outfile=outfile)

    return None


@click.command(
    name="unpublished",
)
@filehandle_r_arg
@tag_arg_opt
@delimiter_opt
@include_opt
@exclude_opt
@na_opt
def prep_unpublished_cmd(
    filename: TextIO,
    tag: Optional[str],
    delimiter: Optional[str],
    include: Optional[str],
    exclude: Optional[str],
    na: Optional[str],
) -> NoReturn:
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

    def _mk_unpublished_fasta_cmd(fh: TextIO) -> Set[Tuple[Node, Node, Node]]:

        (inc, exc, levels) = process_tablelike(include, exclude, None)

        return recipe.IrregularFasta(
            text=fh,
            tag=tag,
            include=inc,
            exclude=exc,
            log=True,
            levels=levels,
            na_str=make_na(na),
        ).connect()

    with_graph(_mk_unpublished_fasta_cmd(filename))

    sys.exit(0)


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


def make_const(url: str, repo: str, outfile: TextIO = sys.stdout) -> None:
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
    import pgraphdb as db

    sparql_filename = os.path.join(os.path.dirname(__file__), "data", "segments.rq")
    results = db.sparql_query(
        sparql_file=sparql_filename, url=url, repo_name=repo
    ).convert()
    formatting.write_constellations(results, outfile=outfile)
    return None


def make_subtypes(url: str, repo: str, outfile: TextIO = sys.stdout) -> None:
    strains, isolates = get_missing_subtypes(url, repo)
    print("strain_name\tsubtype", file=outfile)
    for identifier, subtype in strains + isolates:
        print(f"{identifier}\t{subtype}", file=outfile)


def get_missing_subtypes(
    url: str, repo: str
) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    import octofludb.recipes as recipe
    import pgraphdb as db

    sparql_filename = os.path.join(os.path.dirname(__file__), "data", "subtypes.rq")

    results = db.sparql_query(
        sparql_file=sparql_filename, url=url, repo_name=repo
    ).convert()

    return recipe.mk_subtypes(results)


@click.command(
    name="masterlist",
)
@url_opt
@repo_name_opt
def report_masterlist_cmd(url: str, repo: str) -> NoReturn:
    """
    Generate the surveillance masterlist
    """
    import octofludb.recipes as recipe
    import pgraphdb as db

    sparql_filename = os.path.join(os.path.dirname(__file__), "data", "masterlist.rq")

    results = db.sparql_query(
        sparql_file=sparql_filename, url=url, repo_name=repo
    ).convert()

    recipe.mk_masterlist(results)

    sys.exit(0)


# ===== fetch subcommands =====


@click.command(
    name="tag",
)
@filename_arg
@url_opt
@repo_name_opt
def fetch_tag_cmd(filename: str, url: str, repo: str) -> NoReturn:
    """
    Upload list of tags
    """
    from rdflib import Literal
    from octofludb.nomenclature import make_query_tag_uri, P
    from tempfile import mkstemp

    g = open_graph()
    # get all identifiers
    with open(filename, "r") as fh:
        identifiers = [s.strip() for s in fh.readlines()]

    # make the turtle file
    taguri = make_query_tag_uri()
    g = open_graph()
    for identifier in identifiers:
        g.add((taguri, P.query_tag, Literal(identifier)))
    g.commit()  # just in case we missed anything
    log("Serializing to turtle format ... ", end="")
    turtles = g.serialize(format="turtle")
    log("done")
    (n, turtle_filename) = mkstemp(suffix=".ttl")
    with open(turtle_filename, "w") as th:
        for line in turtles.splitlines():
            print(line, file=th)

    # upload it to the database
    upload_cmd([turtle_filename], url, repo)
    g.close()

    sys.exit(0)


@click.command(
    name="isolate",
)
@url_opt
@repo_name_opt
def fetch_isolate_cmd(url: str, repo: str) -> NoReturn:
    """
    Fetch tagged isolate data
    """
    sparql_filename = os.path.join(
        os.path.dirname(__file__), "data", "get-tagged-isolate.rq"
    )
    fmt_query_cmd(sparql_filename, header=True, fasta=False, url=url, repo=repo)

    sys.exit(0)


@click.command(
    name="strain",
)
@url_opt
@repo_name_opt
def fetch_strain_cmd(url: str, repo: str) -> NoReturn:
    """
    Fetch tagged strain data
    """
    sparql_filename = os.path.join(
        os.path.dirname(__file__), "data", "get-tagged-strain.rq"
    )
    fmt_query_cmd(sparql_filename, header=True, fasta=False, url=url, repo=repo)

    sys.exit(0)


@click.command(
    name="segment",
)
@url_opt
@repo_name_opt
def fetch_segment_cmd(url: str, repo: str) -> NoReturn:
    """
    Fetch tagged segment data
    """
    sparql_filename = os.path.join(
        os.path.dirname(__file__), "data", "get-tagged-segment.rq"
    )
    fmt_query_cmd(sparql_filename, header=True, fasta=False, url=url, repo=repo)

    sys.exit(0)


@click.command(
    name="sequence",
)
@url_opt
@repo_name_opt
def fetch_sequence_cmd(url: str, repo: str) -> NoReturn:
    """
    Fetch tagged sequence data
    """
    sparql_filename = os.path.join(
        os.path.dirname(__file__), "data", "get-tagged-sequence.rq"
    )
    fmt_query_cmd(sparql_filename, header=False, fasta=True, url=url, repo=repo)

    sys.exit(0)


@click.command(
    name="clear",
)
@url_opt
@repo_name_opt
def fetch_clear_cmd(url: str, repo: str) -> NoReturn:
    """
    Clear all uploaded tags
    """
    import pgraphdb as db

    sparql_filename = os.path.join(
        os.path.dirname(__file__), "data", "clear-query-tags.rq"
    )
    db.update(sparql_file=sparql_filename, url=url, repo_name=repo)

    sys.exit(0)


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
fetch_grp.add_command(fetch_sequence_cmd)
fetch_grp.add_command(fetch_clear_cmd)


# ===== report subcommands =====


def macro_query(
    filename: str, macros: List[Tuple[str, str]], *args, **kwargs
) -> TextIO:
    """
    Expand macros in a SPARQL query file
    """

    import re
    from tempfile import mkstemp

    sparql_filename = os.path.join(os.path.dirname(__file__), "data", filename)

    (n, tmpfile) = mkstemp(suffix=".rq")

    with open(sparql_filename, "r") as template:
        with open(tmpfile, "w") as query:
            for line in template.readlines():
                for (macro, replacement) in macros:
                    line = re.sub(macro, replacement, line)
                print(line, file=query)

    result = fmt_query_cmd(tmpfile, *args, **kwargs)

    os.remove(tmpfile)

    return result


@click.command(
    name="monthly",
)
@click.argument("year", type=click.IntRange(min=2009, max=2100))
@click.argument("month", type=click.IntRange(min=1, max=12))
@click.option("--context", is_flag=True, help="Get contextualizing sequences")
@url_opt
@repo_name_opt
def report_monthly_cmd(year, month, context, url, repo):
    """
    Surveillance data for the given month (basis of WGS selections)
    """

    def pad(x):
        if x < 10 and x >= 0:
            return "0" + str(x)
        else:
            return str(x)

    if context:

        macros = [
            ("__MIN_DATE__", f"{str(year - 1)}-{pad(month)}-01"),
            ("__MAX_DATE__", f"{str(year + 1)}-{pad(month)}-01"),
        ]

        macro_query(
            "monthly-context.rq", macros, header=True, fasta=True, url=url, repo=repo
        )

    else:

        macros = [("__YEAR__", str(year)), ("__MONTH__", str(month))]

        macro_query("wgs.rq", macros, header=True, fasta=False, url=url, repo=repo)


@click.command(
    name="quarter",
)
@url_opt
@repo_name_opt
def report_quarter_cmd(url, repo):
    """
    Surveillance data for the quarter (basis of quarterly reports)

    Currently, this just generates the smae masterlist as is used in
    octoflushow. However, it may eventually be specialized.
    """
    report_masterlist_cmd(url=url, repo=repo)


@click.command(
    name="offlu",
)
@url_opt
@repo_name_opt
def report_offlu_cmd(url, repo):
    """
    Synthesize public and private data needed for offlu reports
    """
    raise NotImplementedError


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


report_grp.add_command(report_offlu_cmd)
report_grp.add_command(report_monthly_cmd)
report_grp.add_command(report_quarter_cmd)
report_grp.add_command(report_masterlist_cmd)

# ===== deletion subcommands =====


@click.command(
    name="constellations",
)
@url_opt
@repo_name_opt
def delete_constellations_cmd(url: str, repo: str) -> NoReturn:
    """
    Delete all constellation data
    """
    import octofludb.script as script
    import pgraphdb as db

    delete_script = script.get_data_file("delete-constellations.rq")
    db.update(sparql_file=delete_script, url=url, repo_name=repo)

    sys.exit(0)


@click.command(
    name="subtypes",
)
@url_opt
@repo_name_opt
def delete_subtypes_cmd(url: str, repo: str) -> NoReturn:
    """
    Delete all subtype data
    """
    import octofludb.script as script
    import pgraphdb as db

    delete_script = script.get_data_file("delete-subtypes.rq")
    db.update(sparql_file=delete_script, url=url, repo_name=repo)

    sys.exit(0)


@click.command(
    name="us-clades",
)
@url_opt
@repo_name_opt
def delete_us_clades_cmd(url: str, repo: str) -> NoReturn:
    """
    Delete all clade data
    """
    import octofludb.script as script
    import pgraphdb as db

    delete_script = script.get_data_file("delete-us_clades.rq")
    db.update(sparql_file=delete_script, url=url, repo_name=repo)

    sys.exit(0)


@click.command(
    name="gl-clades",
)
@url_opt
@repo_name_opt
def delete_gl_clades_cmd(url: str, repo: str) -> NoReturn:
    """
    Delete all global H1 clade data
    """
    import octofludb.script as script
    import pgraphdb as db

    delete_script = script.get_data_file("delete-gl_clades.rq")
    db.update(sparql_file=delete_script, url=url, repo_name=repo)

    sys.exit(0)


@click.command(
    name="motifs",
)
@url_opt
@repo_name_opt
def delete_motifs_cmd(url: str, repo: str) -> NoReturn:
    """
    Delete all antigenic motifs
    """
    import octofludb.script as script
    import pgraphdb as db

    delete_script = script.get_data_file("delete-motifs.rq")
    db.update(sparql_file=delete_script, url=url, repo_name=repo)

    sys.exit(0)


@click.group(
    cls=OrderedGroup,
    name="delete",
    context_settings=CONTEXT_SETTINGS,
)
def delete_grp():
    """
    Delete datasets. This can be useful when the dataset is corrupted in some
    way. For example, if you changed clade names in your octoFLU reference file
    and then reran `octofludb pull`, no change would occur since only strains
    with missing clades are updated. Instead you would need to first delete the
    existing clades and restart. If instead you manually ran octoFLU, built a
    turtle file from the resulting file, and uploaded that, then you could end
    up with multiple clades associated with some sequences.
    """
    pass


delete_grp.add_command(delete_constellations_cmd)
delete_grp.add_command(delete_subtypes_cmd)
delete_grp.add_command(delete_us_clades_cmd)
delete_grp.add_command(delete_gl_clades_cmd)
delete_grp.add_command(delete_motifs_cmd)


@click.group(cls=OrderedGroup, context_settings=CONTEXT_SETTINGS)
@click.version_option(__version__, "-v", "--version", message=__version__)
def cli_grp():
    """
    API and utilities for the USDA swine IVA surveillance database
    """
    pass


cli_grp.add_command(init_cmd)
cli_grp.add_command(pull_cmd)
cli_grp.add_command(query_cmd)
cli_grp.add_command(update_cmd)
cli_grp.add_command(classify_cmd)
cli_grp.add_command(construct_cmd)
cli_grp.add_command(upload_cmd)
cli_grp.add_command(prep_grp)
cli_grp.add_command(fetch_grp)
cli_grp.add_command(report_grp)
cli_grp.add_command(delete_grp)


def main():
    cli_grp()
