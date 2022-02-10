from __future__ import annotations
from typing import Optional, Tuple

import itertools
import rdflib
import urllib.parse as url
import sys
import re
import octofludb.domain_geography as geo
import octofludb.domain_date as date
from rdflib.namespace import RDFS, OWL, XSD
from rdflib.term import Node
from octofludb.util import padDigit

ni = rdflib.Namespace("https://flu-crew.org/id/")
nt = rdflib.Namespace("https://flu-crew.org/term/")
ntag = rdflib.Namespace("https://flu-crew.org/tag/")
nquery = rdflib.Namespace("https://flu-crew.org/query/")
nusa = rdflib.Namespace("https://flu-crew.org/geo/country/usa/")
ncountry = rdflib.Namespace("https://flu-crew.org/geo/country/")

manager = rdflib.namespace.NamespaceManager(rdflib.Graph())
manager.bind("fid", ni)
manager.bind("f", nt)
manager.bind("usa", nusa)
manager.bind("world", ncountry)
manager.bind("query", nquery)


def make_tag_uri(x: str) -> Node:
    tag = x.strip().replace(" ", "_").lower()
    tag = url.quote_plus(tag)
    return ntag.term(tag)


def make_query_tag_uri(x="default") -> Node:
    tag = url.quote_plus(x)
    return nquery.term(tag)


def define_subproperty(p1: Node, p2: Node) -> Optional[Tuple[Node, Node, Node]]:
    """
    define p1 as a subproperty of p2 in graph g

    return None if the nodes are the same
    """
    if p1 != p2:
        return (p1, RDFS.subPropertyOf, p2)
    else:
        return None


def uidgen(base="_", pad=3, start=0):
    base = base.replace(" ", "_")
    for i in itertools.count(0):
        yield ni.term(padDigit(base + str(i), pad))


def make_uri(x, namespace=ni) -> Optional[Node]:
    if not x:
        return None
    if isinstance(x, rdflib.term.URIRef):
        return x
    else:
        x = re.sub("[ -]+", "_", x.strip()).lower()
        return namespace.term(url.quote_plus(x))


def make_usa_state_uri(code):
    abbr = geo.state_to_code(code)
    if not abbr:
        print(
            f"Expected a USA state name or postal abbreviation, found '{code}'",
            file=sys.stderr,
        )
        sys.exit(1)
    return nusa.term(abbr)


def make_country_uri(countryStr):
    code = geo.country_to_code(countryStr)
    if code:
        uri = ncountry.term(code)
    else:
        uri = make_uri(countryStr, namespace=ncountry)
    return uri


def make_country_uri_from_code(code: str) -> Node:
    return ncountry.term(code)


def make_date(dateStr) -> Optional[Node]:
    try:
        # Parse this to a date if it is of the pandas date type
        # This will remove any time annotation
        dateStr = str(dateStr.date())
    except AttributeError:
        pass
    try:
        uri = date.p_any_date.parse_strict(dateStr).as_uri()
    except:
        uri = None
    return uri


def make_property(x: str) -> Node:
    return nt.term(x.lower().replace(" ", "_"))


def make_literal(x, infer=True) -> Node:
    if not infer:
        return rdflib.Literal(x)
    try:
        # Can x be a date?
        return rdflib.Literal(str(date.p_date.parse(x)), datatype=XSD.date)
    except:
        return rdflib.Literal(x)


def make_integer(x):
    return rdflib.Literal(x, datatype=XSD.integer)


class O:
    feature: Node = nt.Feature
    unknown_strain: Node = nt.unknown_strain
    unknown_unknown: Node = nt.unknown


class P:
    # standard semantic web predicates
    name: Node = nt.name  # in scheme: rdfs:label rdfs:subPropertyOf f:name
    abbr: Node = nt.abbr
    sameAs: Node = OWL.sameAs
    unknown_unknown: Node = nt.unknown
    chksum: Node = nt.chksum
    # flu relations
    has_feature: Node = nt.has_feature
    tag: Node = nt.tag
    query_tag: Node = nt.query_tag
    dnaseq: Node = nt.dnaseq
    proseq: Node = nt.proseq
    global_clade: Node = nt.global_clade
    constellation: Node = nt.constellation
    segment_name: Node = nt.segment_name
    segment_number: Node = nt.segment_number
    unknown_strain: Node = nt.unknown_strain
    # blast predicates
    qseqid: Node = nt.qseqid
    sseqid: Node = nt.sseqid
    pident: Node = nt.pident
    length: Node = nt.length
    mismatch: Node = nt.mismatch
    gapopen: Node = nt.gapopen
    qstart: Node = nt.qstart
    qend: Node = nt.qend
    sstart: Node = nt.sstart
    send: Node = nt.send
    evalue: Node = nt.evalue
    bitscore: Node = nt.bitscore
    # labels for sequences
    gb: Node = nt.genbank_id
    epi_id: Node = nt.epi_id
    # labels for strains
    strain_name: Node = nt.strain_name
    barcode: Node = nt.barcode
    epi_isolate: Node = nt.epi_isolate
    has_segment: Node = nt.has_segment
    # the local curated data
    ref_reason: Node = nt.ref_reason
    country: Node = nt.country
    country_name: Node = nt.country_name
    state: Node = nt.state
    subtype: Node = nt.subtype
    ha_clade: Node = nt.ha_clade
    na_clade: Node = nt.na_clade
    date: Node = nt.date
    time: Node = nt.time
    file: Node = nt.file
    host: Node = nt.host
    encodes: Node = nt.gene
    # -----------------------------------------------------------------------
    # gb/*  -- I need to start generalizing away from this, since this data
    # does not come only from genebank.
    # -----------------------------------------------------------------------
    feature_key: Node = nt.feature_key
    gb_locus: Node = nt.locus  # unique key
    gb_length: Node = nt.length
    gb_strandedness: Node = nt.strandedness
    gb_moltype: Node = nt.moltype
    gb_topology: Node = nt.topology
    gb_division: Node = nt.division
    gb_update_date: Node = nt.update_date
    gb_create_date: Node = nt.create_date
    gb_definition: Node = nt.definition
    gb_primary_accession: Node = nt.primary_accession
    gb_accession_version: Node = nt.accession_version
    gb_other_seqids: Node = nt.other_seqids
    gb_source: Node = nt.source
    gb_organism: Node = nt.organism
    gb_taxonomy: Node = nt.taxonomy
    gb_references: Node = nt.references
    gb_sequence: Node = nt.sequence
    # -----------------------------------------------------------------------
    # gb/feature/*
    # -----------------------------------------------------------------------
    # a set of features associated with this particular strain
    gb_key: Node = nt.key  # feature type (source | gene | CDS | misc_feature)
    gb_location: Node = nt.location
    gb_intervals: Node = nt.intervals
    gb_operator: Node = nt.operator
    # a set of qualifiers for this feature
    # in biopython, this is a list of
    # {'GBQualifier_value' 'GBQualifier_name'} dicts
    gb_codon_start: Node = nt.codon_start
    gb_collection_date: Node = nt.collection_date
    gb_country: Node = nt.country
    gb_db_xref: Node = nt.db_xref
    gb_gene: Node = nt.gene
    gb_host: Node = nt.host
    gb_isolation_source: Node = nt.isolation_source
    gb_mol_type: Node = nt.mol_type
    gb_note: Node = nt.note
    gb_product: Node = nt.product
    gb_protein_id: Node = nt.protein_id
    gb_serotype: Node = nt.serotype
    gb_strain: Node = nt.strain_name
    gb_transl_table: Node = nt.transl_table
    gb_translation: Node = nt.translation
