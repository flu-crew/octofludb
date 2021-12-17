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

## Help

You can get a list of subcommands with `octofludb -h`. More detailed
documentation is available for each subcommand, e.g., `octofludb query -h`.

## Subcommands

`octofldub` has builtin documentation for each subcommand that describes the
all arguments and general usage. Below I will cover each of the subcommands at
a higher level with examples and background info as needed.

### Subcommand: `init` - initialize an empty octofludb database

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

### Subcommand: `pull` - update data

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

### Subcommand: `query` - submit a SPARQL query

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

To explore the relations in the database, you can run queries such as the following:

```sparql
PREFIX f: <https://flu-crew.org/term/>
SELECT ?gid ?p ?o WHERE {
    ?sid f:has_segment ?gid .
    ?sid f:host "swine" .
    ?gid f:segment_name "HA" .
    ?gid f:clade ?clade .
    ?gid ?p ?o .
}
LIMIT 100
```

This gives you a list of links from a swine segment to other data. 

### Subcommand: `update` - submit a SPARQL deletion statement 

Like `octofludb query`, `octofludb update` also takes a SPARQL file. They are
called in different ways since `query` is a readonly call and `update` can
delete values from the database. I have only used `update` for deletion, though
it can also insert data.

Use this command with care -- deletion can't be undone. When possible, use the
`octofludb delete` subcommand to delete specific selections of data (such as a
clades or all motifs).

As an example, say you want to reclassify the all strains in the 1C lineage.
You can do this by updating the octoFLU reference file and running:

```
octofludb pull --no-subtype --no-motifs --no-schema --no-motifs --nmonths=0
```

This will just run the classification step.

However, it changes nothing, because `octofludb` finds that all the 1C's are
already annotated tries to save you time by not passing them to octoFLU.

You could create your own table of data linking genbank ids to clades with
`octofludb prep table`. But then you would end up with *two* clades for each 1C
strain. The triplestore doesn't *know* that this relationship should be unique
(there is a way toto give it this information, but let's save that for later).

Instead, we need to specifically delete the 1C clades triples. This can be done
with `octofludb update` and the following SPARQL file:

```sparql
DELETE {
    ?sid f:gl_clade ?clade .
} WHERE {
    ?sid f:gl_clade ?clade .
    FILTER(REGEX(?clade, "1C")) .
}
```

You can check that octofludb did indeed delete the 1C clades with the query:

```sparql
SELECT ?sid ?clade .
} WHERE {
    ?sid f:gl_clade ?clade .
    FILTER(REGEX(?clade, "1C")) .
}
```

Which should return nothing.

### Subcommand: `delete` - delete 

`octofludb delete` can be used as an alternative to the lower-level `octofludb
update` SPARQL calls described above. It deletes specific kinds of data, such
as all constellations, all subtypes, all us-clades, and global clades, or all
motifs.

### Subcommand: `construct` - submit a SPARQL construction statement

Honestly, I never use this subcommand and am not sure if it works. Maybe I
should remove it?

### Subcommand: `prep` - munge data into Turtle files

If you want to work with data beyond that which `octofludb pull` loads, then
you will need `prep`. This subcommand parses data out of various formats and
writes it into Turtle files that can be uploaded to the database.

The different file formats `prep` supports are available as a list of
sub-subcommands. The three most important of these are `fasta`, `table`, and
`unpublished`. The other sub-subcommands are slated for deprecation.

Internally, `octofludb` tries to fit a FASTA file to a table where columns are
derived from the headers and the last column is the sequences. The default
delimiter for a FASTA header is '|'. So the following FASTA file:

```
>A/swine/R123456/Iowa/2020|H3N2|2020-06-21
GATACAGATACAGATACAGATACAGATACAGATACA
>A/horse/T4343/Canada/2020|H1N2|2020-07-04
CATCATCATCATCATCATCATCATCATCATCATCAT
```

Would be viewed internally as the table:

```
strain_name               subtype  date       dnaseq
A/swine/R123456/Iowa/2020 H3N2     2020-06-21 GATACA...
A/horse/T4343/Canada/2020 H1N2     2020-07-04 CATCAT...
```

`octofludb` will attempt to guess the type of each column. The each element in
the first field match the parser for the `strain_name` type, the second field
matches the parser for subtype, the third for date, the fourth for dna
sequence. But here `octofludb` hits a snag. How should the DNA sequence be
connected to the strain name? Strains don't have DNA sequences. Only the
segments do. This query shows the problem:

```sparql
PREFIX f: <https://flu-crew.org/term/>

SELECT ?strain ?seq
WHERE {
    ?sid f:strain_name ?strain .
    ?sid f:has_segment ?gid .
    ?gid f:dnaseq ?seq .
}
```

A strain in `octofludb` is linked to many segments UUIDs. Each segment UUID is
linked to a DNA sequence. The UUIDs for segments are usually derived from the
genbank or epiflu ids. For example, `MW872131` is translated to the UUID
`<https://flu-crew.org/id/mw872131>`. Because there is a deterministic way of
mapping a GenBank id to a UUID, any new data that comes in that is associated
with a known GenBank ID can be automatically linked. But in the above FASTA, no
ID is specified for the segment.

`octofludb` circumvents this issue by using the md5 hash of the DNA sequence as
the base of the UUID. This will merge together segments that have duplicate
sequences. So `octofludb prep fasta` will produce the turtle file:

```turtle
@prefix f: <https://flu-crew.org/term/> .
@prefix fid: <https://flu-crew.org/id/> .
@prefix usa: <https://flu-crew.org/geo/country/usa/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<https://flu-crew.org/id/a%2Fhorse%2Ft4343%2Fcanada%2F2020> f:date "2020-07-04"^^xsd:date ;
    f:has_segment fid:e7e8df44044f1ee2b4fd9e60b33efe9a ;
    f:strain_name "A/horse/T4343/Canada/2020" ;
    f:subtype "H1N2" .

<https://flu-crew.org/id/a%2Fswine%2Fr123456%2Fiowa%2F2020> f:date "2020-06-21"^^xsd:date ;
    f:has_segment fid:1ca74a6402f97cf38907d194bf6b837a ;
    f:state usa:IA ;
    f:strain_name "A/swine/R123456/Iowa/2020" ;
    f:subtype "H3N2" .

fid:1ca74a6402f97cf38907d194bf6b837a f:chksum "1ca74a6402f97cf38907d194bf6b837a" ;
    f:dnaseq "GATACAGATACAGATACAGATACAGATACAGATACA" .

fid:e7e8df44044f1ee2b4fd9e60b33efe9a f:chksum "e7e8df44044f1ee2b4fd9e60b33efe9a" ;
    f:dnaseq "CATCATCATCATCATCATCATCATCATCATCATCAT" .
```

Whenever you use `octofludb prep`, you should always double check the resulting
Turtle files before uploading them to the database to ensure the right
information is being pushed.

### Subcommand: `upload` - upload one or more Turtle files

Not much to say here, the `upload` command uploads Turtle files to the
database. Any triples that are already present in the database are ignored.

### Subcommand: `classify` - classify strains with octoFLU

`octofludb classify` takes a fasta file as an argument and produces a table
showing the clades. It is a wrapper around octoFLU that uses the locally
specified reference file. The path to this reference file may be specified in
the `~/.octofludb/config.yaml` file. If no reference file is specified, the
default octoFLU reference is used.

### Subcommand: `report` - make specialized reports

Any report generating logic that is important enough to crystallize into
octofludb itself, that is comprised of both a query and filtering/cleaning in
Python, should be added here.

There are currently two useful reports.

The first is `octofludb report masterlist`. This produces the file that is the input to octoflushow and the quarterly reports.

The second is `octofludb report monthly`. This produces the input to the monthly WGS selection pipeline.

There are currently two other commands: `offlu` and `quarter`. `offlu` is a
stub that will eventually produce the public and gisaid inputs to the VCM-offlu
pipeline. `quarter` is currently just a wrapper around `masterlist`, since both
octoflushow and the quarterly report use the same input.

### Subcommand: `fetch` - tag and fetch sets of identifiers

`octofludb fetch` contains a selection of tools for working with specific sets of identifiers.

For example

```
octofludb fetch tag id-list.txt
```

Will read all the ids in id-list and associate them all with a unique tag. The
ids may be strain names, genbank ids, epiflu ids, epiflu isolate ids, or
barcodes. `octofludb` understands all these ids and will figure out the right
thing for you.

Once your ids are tagged, you can retrieve them with the sub-subcommands:
`isolate`, `strain`, `segment`, or `sequence`. Each of these commands pulls the
tagged data at a different level.

The tags may also be used in SPARQL queries.

Here is an longer example. Suppose you have a mysterious list of 10 genbank ids in a file named `mystery.txt`:

```
EPI653195
CY246223
JX983103
MF801489
JN652492
CY099224
MF145504
HQ896660
KM503168
JF316643
```

First you want to clear any previous tags:

```
octofludb fetch clear
```

Then tag your mystery ids:

```
octofludb fetch tag `mystery.txt`
```

Now you view default sections of your data. Try all the following:

```
octofludb fetch segment
octofludb fetch strain 
octofludb fetch isolate
octofludb fetch sequence
```

You may also specify the tagged terms in a SPARQL query:

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

    # limit the query to tagged segments
    ?tag_id f:query_tag ?tag .
    ?gid f:genbank_id ?tag .

}
```


## Problem strain examples

Here is a (*very incomplete*) list of strange strain names I have to deal with:

  * `A/USA/LAN_(P10)_NA/2018` - parentheses
  * `A/R(duck/Hokkaido/9/99-tern/South Africa/1961)` - worse parentheses
  * `A/swine/Denmark/18-13002-73_PB1/2018` - includes segment name (there are lots of these)
  * `A/swine/Cotes d'Armor/110466/2010` - single quotes
