[![stable](http://badges.github.io/stability-badges/dist/experimental.svg)](http://github.com/badges/stability-badges)
[![Build Status](https://travis-ci.org/flu-crew/octofludb.svg?branch=master)](https://travis-ci.org/flu-crew/octofludb)
![PyPI](https://img.shields.io/pypi/v/octofludb.svg)

# octofludb

Manage the flu-crew swine surveillance database

## Installation

`octofludb` is most easily installed through PyPi:

```
pip install octofludb
```

You may need to replace `pip` with `pip3` on your system.

`octofludb` is also dependent on the GraphDB database, which is a triplestore
database to which all data is pushed. Go to https://graphdb.ontotext.com and
download the GraphDB Free version.

## Configuration

## Help

You can get a list of subcommands with `octofludb -h`. More detailed
documentation is available for each subcommand, e.g., `octofludb query -h`.

## Subcommand: `init` - initialize an empty octofludb database

To start a new database, first you have to call the daemon:

```
$ graphdb -d
```

Then initialize the octofludb database:

```
$ octofludb init
```

If an octofludb repo is already present in GraphDB, this command does nothing.
It will NOT destroy an existing database, so is always safe to run.

If you want to destroy the database and rebuild, then you can use `pgraphdb`.
This is a Python wrapper around GraphDB that is used internally throughout
`octofludb`. It can be installed with pip: `pip3 install pgraphdb`.

```
pgraphdb rm_repo octofludb
```

## Subcommand: `pull` - update data

Use of this command requires some understanding of the `octofludb` configuration.

The `octofludb` home directory is `~/.octofludb`. This directory will is
created when you call `octofludb init` and the default configuration file
`config.yaml` is copied into it. The `config.yaml` file is well documented and
whatever it says is more likely to be true that what I write here, so please
look it over. In short, it specifies where the data can be found `octofludb`
needs can be found.

A particularly important field is `octoflu_reference`, which allows you to
specify a local reference fasta file that will be used by octoFLU to classify
all strains.

The command `octofludb pull`, without any additional flags, will do the
following:

 * Go to the `$OCTOFLUDB_HOME/build` directory (create it if it doesn't exist)

 * Load the local `config.yaml` file

 * Load the `schema.ttl` and `geography.ttl` Turtle files. These are both
   stored in the `octofludb` python package in the `octofludb/data` folder.
   The `schema.ttl` file includes logical relationships such as subProperty
   relationship between H1 and HA that allows the database to infer that a
   subject is an HA if it is an H1. The `geography.ttl` file includes,
   hierarchical relationships between countries and regions (Iowa is in the USA
   and the USA is in North America) and the relationships between country names
   (United Arab Emirates) and ISO country codes (ARE).

 * Retrieve and process all Influenza A Virus data from GenBank. This step will
   take a long time. Most of a day. There are two ways to speed this up. First,
   if you are building a new repo, and `octofludb`'s GenBank processing code
   hasn't changed, you can go to your `~/.octofludb/build` directory and run
   `octofludb upload .gb*ttl`. This will upload all the past GenBank turtle
   files. Of course, you can also copy over someone else's files. It is safe to
   re-upload the same files many times -- no duplicate triples will be created.
   Second, if you are already mostly up-to-date and just need to add the latest
   few months of GenBank data, you can add a `--nmonths=4` argument to just
   pull the data submitted in the last 4 months. All data is pulled by
   *submission* date, NOT *collection* date, so incrementally pulling the last
   few months every month will be fine.

 * (OPTIONAL) if the `--include-gisaid` flag is included, and if paths to
   gisaid sequence and metadata files are in the `config.yaml` file, then
   gisaid data will be parsed and uploaded.

 * All unclassified swine sequences are classified with octoFLU using the
   reference file listed in `config.yaml` or if this field is missing, the
   default octoFLU reference.

 * The subtype of each strain is determined. GenBank has a subtype annotation
   under the `serotype` field, `octoFLU` also determines the subtype of the HA
   and NA, and for gisaid a `gisaid_subtype` field is extracted. `octofludb`
   synthesizes all this info to create one subtype. If there are conflicts, the
   octoFLU subtype is given priority followed by the GenBank subtype. **NOTE:**
   due to a performance bug in the python rdflib library, this step can take a
   long time to serialize to a turtle file, you'll have have to wait for it.

 * H1 and H3 antigenic motifs are determined from the HA sequences using the
   `flutile` module.

## Subcommand: `query` - submit a SPARQL query

Once you've uploaded your data, you will want to access it. This is done with
`octofludb query`. Data is pulled using SPARQL queries. SPARQL is a query
language for accessing data in a triplestore database, just like SQL is a query
language for relational databases. There are no join statements in SPARQL. A
triplestore is, in principle, nothing more than a long list of subject,
predicate, object triples. A SPARQL query defines a pattern over these triples
and returns every set of values for which the pattern is true.

Here is a simple example:

```sparql
PREFIX f: <https://flu-crew.org/term/>

SELECT ?strain ?host ?genbank_id ?country_code ?date
WHERE {
    ?sid f:strain_name ?strain .
    ?sid f:host ?host .
    ?sid f:date ?date .
    ?sid f:country ?country .
    ?country f:code ?country_code .
}
LIMIT 10
```

The first line defines our unique flu-crew namespace, this ensures there are no
name conflicts if we link this database to other SPARQL databases.

The `SELECT` line determines which columns are in the returned table.

The `WHERE` block is a set of patterns that defines what is returned.

All subjects and relations in a triplestore are UUIDs. Objects (such as
`?strain` or `?country`) may be values or UUIDs. So `?sid` is some UUID such
that it has one or more `f:strain_name` edges, one or more `f:host` edges, one
or more `f:date` edges, and one or more `f:code` edges. Countries are stored
both by name and by 3-letter ISO code. `?country` is a UUID that links to the
literal code and name strings. The final two lines of the `WHERE` clause could
alternatively be written as `?sid f:country/f:code ?country_code`.

The final line `LIMIT 10` limits the return data to just 10 entries. I often
place limits on queries while I am building them.

While tables are often needed, in most of our pipelines we would rather have
FASTA files with annotated headers. This can be accomplished by adding the
`--fasta` flag to the `octofludb query` command and placing sequence data as
the final entry in the SELECT statement. For example:

```sparql
PREFIX f: <https://flu-crew.org/term/>

SELECT ?strain ?host ?genbank_id ?country_code ?date ?seq
WHERE {
    ?sid f:strain_name ?strain .
    ?sid f:host ?host .
    ?sid f:date ?date .
    ?sid f:country ?country .
    ?country f:code ?country_code .
    ?sid f:has_segment ?gid .
    ?gid f:segment_name "HA" .
    ?gid f:dnaseq ?seq .
}
LIMIT 10
```

I usually pass sequences through `smof` to clean them up:

```
$ octofludb query --fasta myquery.rq | smof clean -t n -drux > myseqs.fna
```

For an example of complete with filters, aggregate, and optional data, see the
`*.rq` query files in the `octofludb/data` folder of the `octofludb` git repo.

## Subcommand: `update` - submit a SPARQL deletion statement 

## Subcommand: `construct` - submit a SPARQL construction statement

## Subcommand: `prep` - munge data into Turtle files

## Subcommand: `upload` - upload one or more Turtle files

## Subcommand: `classify` - classify strains with octoFLU

## Subcommand: `make` - make various datasets

## Subcommand: `report` - make specialized reports

## Subcommand: `fetch` - tag and fetch sets of identifiers

## Subcommand: `delete` - delete 

## Problem strain examples

    `A/USA/LAN_(P10)_NA/2018`
    `A/R(duck/Hokkaido/9/99-tern/South Africa/1961)`
