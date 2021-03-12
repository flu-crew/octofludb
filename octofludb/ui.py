#!/usr/bin/env python3

import os
import sys
import signal
import pgraphdb as db
import click
import textwrap
import requests
import octofludb.cli as cli
from octofludb.util import log

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

url_opt = click.option("--url", help="GraphDB URL", default="http://localhost:7200")

repo_name_opt = click.option("--repo", help="Repository name", default="octofludb")

tag_arg_pos = click.argument("tag")

tag_arg_opt = click.option(
    "--tag", help="A tag to associate with each identifier", type=str
)

sparql_filename_pos = click.argument("sparql_filename", type=click.Path(exists=True))

all_the_turtles = click.argument(
  "turtle_filenames",
  type=click.Path(exists=True),
  nargs=-1
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


@click.command(
    name="init",
    help="Initialize an empty octofludb database",
)
@url_opt
@repo_name_opt
def init_cmd(*args, **kwargs):
    raise NotImplemented


@click.command(
    name="clean",
    help="clean the database (not yet implemented)",
)
@url_opt
@repo_name_opt
def clean_cmd(*args, **kwargs):
    raise NotImplemented


@click.command(
    name="query",
    help="Submit a SPARQL query to octofludb",
)
@sparql_filename_pos
@header_opt
@fasta_opt
@url_opt
@repo_name_opt
def query_cmd(*args, **kwargs):
    raise NotImplemented


@click.command(
    name="update",
    help="Submit a SPARQL delete or insert query to octofludb"
)
@sparql_filename_pos
@url_opt
@repo_name_opt
def update_cmd(*args, **kwargs):
    raise NotImplemented


#  # upload      Upload one or more turtle files to the database
#  cli_grp.add_command(upload_cmd)
@click.command(
    name="upload",
    help="Upload one or more turtle files to the database"
)
@all_the_turtles
@url_opt
@repo_name_opt
def upload_cmd(*args, **kwargs):
    raise NotImplemented


@click.group(
    name="input",
    help="Various recipes for prepping data for uploading",
    context_settings=CONTEXT_SETTINGS,
)
def input_grp():
  pass


@click.group(
    name="make",
    help="Derive constellations, subtypes, motifs and such",
    context_settings=CONTEXT_SETTINGS,
)
def make_grp():
  pass


@click.group(
    name="fetch",
    help="Recipes for fetching data",
    context_settings=CONTEXT_SETTINGS,
)
def fetch_grp():
  pass


@click.group(
    name="report",
    help="Build standardized reports from the data",
    context_settings=CONTEXT_SETTINGS,
)
def report_grp():
  pass


@click.group(
    name="delete",
    help="Remove data from the database in various ways",
    context_settings=CONTEXT_SETTINGS,
)
def delete_grp():
  pass





#  cli_grp.add_command(input_cmd)
#      #  tag         Associate list of IDs with a tag
#      #  ivr         Translate an IVR table to RDF
#      #  ird         Translate an IRD table to RDF
#      #  gis         Translate a Gisaid metadata excel file to RDF
#      #  gbids       Retrieve data for a list of genbank ids
#      #  update_gb   Retrieve any missing genbank records. Results are stored in
#      #              files with the prefix '.gb_###.ttl'.
#      #  blast       Translate BLAST results into RDF
#      #  table       Translate a table to RDF
#      #  fasta       Translate a fasta file to RDF
#      #  unpublished
#
#  cli_grp.add_command(make_cmd)
#      #  const       Generate constellations for all swine strains.
#      #  subtypes    Determine subtypes based on Genbank serotype field, epiflu
#      #              data, or octoflu HA/NA classifications
#      #  masterlist  Generate the surveillance masterlist
#      #  motifs
#
#  cli_grp.add_command(fetch_cmd) ### push a UUID tag, pull everything through that tag
#      #  A0
#      #  genbank
#      #  gisaid
#
#  cli_grp.add_command(report_cmd)
#      #  monthly     Surveillance data for the given month
#      #  quarter
#      #  offlu
#
#  cli_grp.add_command(delete_cmd)
#      # constellations
#      # subtypes
#      # delete tag
#      # unpublished data


#  parser = argparse.ArgumentParser(
#      prog="octofludb",
#      formatter_class=cli.SubcommandHelpFormatter,
#      description="API and utilities for the swine flu surveillance database",
#      epilog=textwrap.dedent(
#          "Submit issue reports to https://github.com/flu-crew/octofludb/issues"
#      ),
#  )
#  subparsers = parser.add_subparsers(metavar="<subcommand>", title="subcommands")
#  subcommand = cli.subcommand_maker(subparsers)
#
#  url_arg = cli.argument("--url", help="GraphDB URL", default="http://localhost:7200")
#  repo_name_arg = cli.argument("--repo", help="Repository name", default="octofludb")
#  tag_arg_pos = cli.argument("tag", help="A tag to associate with each identifier")
#  tag_arg_opt = cli.argument("--tag", help="A tag to associate with each identifier")
#
#
#  def open_graph():
#      from rdflib import Graph
#      from octofludb.nomenclature import manager
#
#      return Graph(namespace_manager=manager)
#
#
#  def with_graph(f, filename=None, outfile=sys.stdout, *args, **kwargs):
#      g = open_graph()
#
#      if filename is not None:
#          with open(filename, "r") as fh:
#              f(g, fh, *args, **kwargs)
#      else:
#          f(g, *args, **kwargs)
#
#      g.commit()  # just in case we missed anything
#      log("Serializing to turtle format ... ", end="")
#      turtles = g.serialize(format="turtle")
#      log("done")
#      for l in turtles.splitlines():
#          print(l.decode("utf-8"), file=outfile)
#      g.close()
#
#
#  def open_file(path):
#      if path:
#          filehandle = open(args["<filename>"], "r")
#      else:
#          filehandle = sys.stdin
#      return filehandle
#
#
#  def make_na(na_str):
#      if na_str:
#          na_list = na_str.split(",")
#          if isinstance(na_list, list):
#              na_list = [None] + na_str
#          else:
#              na_list = [None, na_list]
#      else:
#          na_list = [None]
#      return na_list
#
#
#  @subcommand(["init", url_arg, repo_name_arg])
#  def call_init_cmd(args):
#      """
#      Initialize an empty octofludb database
#      """
#      config_file = os.path.join(
#          os.path.dirname(__file__), "data", "octofludb-config.ttl"
#      )
#      try:
#          db.make_repo(config=config_file, url=args.url)
#      except requests.exceptions.ConnectionError:
#          print(f"Could not connect to a GraphDB database at {args.url}", file=sys.stderr)
#          sys.exit(1)
#
#
#  @subcommand(
#      [
#          "query",
#          cli.argument("sparql_filename"),
#          cli.argument(
#              "--header",
#              help="Include a header of column names indata returned from query",
#              action="store_true",
#              default=False,
#          ),
#          cli.argument(
#              "--fasta",
#              help="Return query as a fasta file where last column is sequence",
#              action="store_true",
#              default=False,
#          ),
#          url_arg,
#          repo_name_arg,
#      ]
#  )
#  def call_query_cmd(args):
#      """
#      Submit a SPARQL query to octofludb
#      """
#      import octofludb.formatting as formatting
#
#      results = db.sparql_query(
#          sparql_file=args.sparql_filename, url=args.url, repo_name=args.repo
#      )
#      if args.fasta:
#          formatting.write_as_fasta(results)
#      else:
#          formatting.write_as_table(results, header=args.header)
#      sys.exit(0)
#
#
#  @subcommand(["update", cli.argument("sparql_filename"), url_arg, repo_name_arg])
#  def call_update_cmd(args):
#      """
#      Submit a SPARQL delete or insert query to octofludb
#      """
#      db.update(sparql_file=args.sparql_filename, url=args.url, repo_name=args.repo)
#      return None
#
#
#  @subcommand(
#      [
#          "upload",
#          cli.argument(
#              "turtle_filenames", help="One or more turtle filenames", nargs="+"
#          ),
#          url_arg,
#          repo_name_arg,
#      ]
#  )
#  def call_upload_cmd(args):
#      """
#      Upload one or more turtle files to the database
#      """
#      import shutil
#
#      for filename in args.turtle_filenames:
#          new_filename = os.path.join(
#              os.path.expanduser("~"), "graphdb-import", os.path.basename(filename)
#          )
#          if filename == new_filename:
#              continue
#          else:
#              try:
#                  shutil.copyfile(filename, new_filename)
#              except AttributeError as e:
#                  print(
#                      f"Could not move {filename} to {new_filename}: {str(e)}",
#                      file=sys.stderr,
#                  )
#                  sys.exit(1)
#
#      server_files = [os.path.basename(f) for f in args.turtle_filenames]
#
#      db.load_data(url=args.url, repo_name=args.repo, turtle_files=server_files)
#      sys.exit(0)
#
#
#  @subcommand(["tag", cli.argument("filename", help="File of identifiers"), tag_arg_pos])
#  def tag_cmd(args):
#      """
#      Associate list of IDs with a tag
#      """
#      from rdflib import Literal
#      import datetime as datetime
#      from octofludb.nomenclature import make_uri, make_tag_uri, P
#      from octofludb.util import file_str
#
#      g = open_graph()
#      with open(args.filename, "r") as fh:
#          taguri = make_tag_uri(args.tag)
#          g = open_graph()
#          g.add((taguri, P.name, Literal(args.tag)))
#          g.add((taguri, P.time, Literal(datetime.datetime.now())))
#          g.add((taguri, P.file, Literal(file_str(fh))))
#          for identifier in (s.strip() for s in fh.readlines()):
#              g.add((make_uri(identifier), P.tag, taguri))
#          g.commit()  # just in case we missed anything
#          log("Serializing to turtle format ... ", end="")
#          turtles = g.serialize(format="turtle")
#          log("done")
#          for l in turtles.splitlines():
#              print(l.decode("utf-8"))
#      g.close()
#
#
#  @subcommand(["mk_ivr", cli.argument("filename", help="The filename of an IVR table")])
#  def mk_ivr_cmd(args):
#      """
#      Translate an IVR table to RDF
#
#      load big table from IVR, with roughly the following format:
#      gb | host | - | subtype | date | - | "Influenza A virus (<strain>(<subtype>))" | ...
#      """
#      import octofludb.recipes as recipe
#
#      with_graph(recipe.mk_influenza_na, args.filename)
#
#
#  @subcommand(["mk_ird", cli.argument("filename", help="The filename of an IRD table")])
#  def mk_ivr_cmd(args):
#      """
#      Translate an IRD table to RDF
#      """
#      import octofludb.recipes as recipe
#
#      with_graph(recipe.mk_ird, args.filename)
#
#
#  @subcommand(
#      ["mk_gis", cli.argument("filename", help="Path to a Gisaid metadata excel file")]
#  )
#  def mk_gis_cmd(args):
#      """
#      Translate a Gisaid metadata excel file to RDF
#      """
#      import octofludb.recipes as recipe
#
#      with_graph(recipe.mk_gis, args.filename)
#
#
#  def _mk_gbids_cmd(g, gbids=[]):
#      import octofludb.entrez as entrez
#      import octofludb.genbank as gb
#
#      for gb_metas in entrez.get_gbs(gbids):
#          for gb_meta in gb_metas:
#              gb.add_gb_meta_triples(g, gb_meta)
#          # commit the current batch (say of 1000 entries)
#          g.commit()
#
#
#  @subcommand(
#      ["mk_gbids", cli.argument("filename", help="File containing a list of genbank ids")]
#  )
#  def mk_gbids_cmd(args):
#      """
#      Retrieve data for a list of genbank ids
#      """
#      with open(args.filename, "r") as fh:
#          gbids = [gbid.strip() for gbid in fh]
#      log(f"Retrieving and parsing genbank ids from '{args.filename}'")
#      with_graph(_mk_gbids_cmd, gbids=gbids)
#
#
#  @subcommand(
#      [
#          "update_gb",
#          cli.argument("--minyear", help="Earliest year to update", default=1918),
#          cli.argument("--maxyear", help="Latest year to update", default=2099),
#          cli.argument("--nmonths", help="Update Genbank files for the last N months"),
#      ]
#  )
#  def mk_update_gb(args):
#      """
#      Retrieve any missing genbank records. Results are stored in files with the prefix '.gb_###.ttl'.
#      """
#      from octofludb.entrez import missing_acc_by_date
#      import octofludb.colors as colors
#
#      minyear = int(args.minyear)
#      maxyear = int(args.maxyear)
#
#      if args.nmonths is None:
#          nmonths = 9999
#      else:
#          nmonths = int(args.nmonths)
#
#      for date, missing_acc in missing_acc_by_date(
#          min_year=minyear, max_year=maxyear, nmonths=nmonths
#      ):
#          if missing_acc:
#              log(colors.good(f"Updating {date} ..."))
#              outfile = ".gb_" + date.replace("/", "-") + ".ttl"
#              with open(outfile, "w") as fh:
#                  with_graph(_mk_gbids_cmd, gbids=missing_acc, outfile=fh)
#          else:
#              log(colors.good(f"Up-to-date for {date}"))
#
#
#  @subcommand(
#      [
#          "mk_blast",
#          cli.argument("filename", help="File containing a list of genbank ids"),
#          tag_arg_opt,
#      ]
#  )
#  def mk_blast_cmd(args):
#      """
#      Translate BLAST results into RDF
#      """
#      import octofludb.recipes as recipe
#
#      log(f"Retrieving and parsing blast results from '{args.filename}'")
#      with_graph(recipe.mk_blast, args.filename, tag=args.tag)
#
#
#  def process_tablelike(include, exclude, levels):
#      if not include:
#          inc = {}
#      else:
#          inc = set(include.split(","))
#      if not exclude:
#          exc = {}
#      else:
#          exc = set(exclude.split(","))
#      if not levels:
#          levels = None
#      else:
#          levels = {s.strip() for s in levels.split(",")}
#      return (inc, exc, levels)
#
#
#  include_arg = cli.argument(
#      "--include", help="Only parse using these tokens (comma-delimited list)", default=""
#  )
#  exclude_arg = cli.argument(
#      "--exclude", help="Remove these tokens (comma-delimited list)", default=""
#  )
#  na_arg = cli.argument("--na", help="The string that represents a missing value")
#
#
#  @subcommand(
#      [
#          "mk_table",
#          cli.argument("filename", help="Path to a table"),
#          tag_arg_opt,
#          include_arg,
#          exclude_arg,
#          cli.argument("--levels", help="levels"),
#          na_arg,
#      ]
#  )
#  def mk_table_cmd(args):
#      """
#      Translate a table to RDF
#      """
#      import octofludb.classes as classes
#
#      def _mk_table_cmd(g, fh):
#          (inc, exc, levels) = process_tablelike(args.include, args.exclude, args.levels)
#          classes.Table(
#              filehandle=fh,
#              tag=args.tag,
#              include=inc,
#              exclude=exc,
#              log=True,
#              levels=levels,
#              na_str=make_na(args.na),
#          ).connect(g)
#
#      with_graph(_mk_table_cmd, args.filename)
#
#
#  @subcommand(
#      [
#          "mk_fasta",
#          cli.argument("filename", help="Path to a TAB-delimited or excel table"),
#          tag_arg_opt,
#          cli.argument(
#              "--delimiter",
#              help="The delimiter between fields in the header",
#              default="|",
#          ),
#          include_arg,
#          exclude_arg,
#          na_arg,
#      ]
#  )
#  def mk_fasta_cmd(args):
#      """
#      Translate a fasta file to RDF
#      """
#      import octofludb.classes as classes
#
#      def _mk_fasta_cmd(g, fh):
#          (inc, exc, levels) = process_tablelike(args.include, args.exclude, None)
#          classes.Ragged(
#              filehandle=fh,
#              tag=args.tag,
#              include=inc,
#              exclude=exc,
#              log=True,
#              levels=levels,
#              na_str=make_na(args.na),
#          ).connect(g)
#
#      with_graph(_mk_fasta_cmd, args.filename)
#
#
#  @subcommand(["const", url_arg, repo_name_arg])
#  def const_cmd(args):
#      """
#      Generate constellations for all swine strains.
#
#      A constellation is a succinct description of the internal 6 genes. The
#      description consists of 6 symbols representing the phylogenetic clades of
#      the 6 proteins: PB2, PB1, PA, NP, M, and NS. Current US strains should
#      consist of genes from 3 groups: pandemic (P), TRIG (T), and the LAIV
#      vaccine strain (V). "-" indicates that no sequence is available for the
#      given segment. "H" represents a human seasonal internal gene (there are
#      only a few of these in the US. "X" represents something else exotic (e.g.,
#      not US). For mixed strains, the constellation will be recorded as "mixed".
#      """
#      import octofludb.formatting as formatting
#
#      sparql_filename = os.path.join(os.path.dirname(__file__), "data", "segments.rq")
#
#      results = db.sparql_query(
#          sparql_file=sparql_filename, url=args.url, repo_name=args.repo
#      )
#      formatting.write_constellations(results)
#
#
#  @subcommand(["subtypes", url_arg, repo_name_arg])
#  def subtypes(args):
#      """
#      Determine subtypes based on Genbank serotype field, epiflu data, or octoflu HA/NA classifications
#      """
#      import octofludb.recipes as recipe
#
#      sparql_filename = os.path.join(os.path.dirname(__file__), "data", "subtypes.rq")
#
#      results = db.sparql_query(
#          sparql_file=sparql_filename, url=args.url, repo_name=args.repo
#      )
#
#      recipe.mk_subtypes(results)
#
#
#  @subcommand(["masterlist", url_arg, repo_name_arg])
#  def const_cmd(args):
#      """
#      Generate the surveillance masterlist
#      """
#      import octofludb.recipes as recipe
#
#      sparql_filename = os.path.join(os.path.dirname(__file__), "data", "masterlist.rq")
#
#      results = db.sparql_query(
#          sparql_file=sparql_filename, url=args.url, repo_name=args.repo
#      )
#
#      recipe.mk_masterlist(results)


@click.group(
    help="API and utilities for the USDA swine IVA surveillance database",
    context_settings=CONTEXT_SETTINGS
)
def cli_grp():
    pass


cli_grp.add_command(init_cmd)
cli_grp.add_command(clean_cmd)
cli_grp.add_command(query_cmd)
cli_grp.add_command(update_cmd)
cli_grp.add_command(upload_cmd)
cli_grp.add_command(input_grp)
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
