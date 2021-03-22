import itertools
import rdflib
import urllib.parse as url
import sys
import re
import octofludb.domain.geography as geo
import octofludb.domain.date as date
from rdflib.namespace import RDF, RDFS, OWL, XSD
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


def make_tag_uri(x):
    tag = x.strip().replace(" ", "_").lower()
    tag = url.quote_plus(tag)
    return ntag.term(tag)


def make_query_tag_uri(x="default"):
    tag = url.quote_plus(x)
    return nquery.term(tag)


def define_subproperty(p1, p2, g):
    """
    define p1 as a subproperty of p2 in graph g
    """
    if p1 != p2:
        g.add((p1, RDFS.subPropertyOf, p2))


def uidgen(base="_", pad=3, start=0):
    base = base.replace(" ", "_")
    for i in itertools.count(0):
        yield ni.term(padDigit(base + str(i), pad))


def make_uri(x, namespace=ni):
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


def make_country_uri_from_code(code):
    return ncountry.term(code)


def make_date(dateStr):
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


def make_property(x):
    return nt.term(x.lower().replace(" ", "_"))


def make_literal(x, infer=True):
    if not infer:
        return rdflib.Literal(x)
    try:
        # Can x be a date?
        return rdflib.Literal(str(date.p_date.parse(x)), datatype=XSD.date)
    except:
        return rdflib.Literal(x)


class O:
    feature = nt.Feature
    unknown_strain = nt.unknown_strain
    unknown_unknown = nt.unknown


class P:
    # standard semantic web predicates
    name = nt.name  # in scheme: rdfs:label rdfs:subPropertyOf f:name
    abbr = nt.abbr
    sameAs = OWL.sameAs
    unknown_unknown = nt.unknown
    chksum = nt.chksum
    # flu relations
    has_feature = nt.has_feature
    tag = nt.tag
    query_tag = nt.query_tag
    dnaseq = nt.dnaseq
    proseq = nt.proseq
    global_clade = nt.global_clade
    constellation = nt.constellation
    segment_name = nt.segment_name
    segment_number = nt.segment_number
    unknown_strain = nt.unknown_strain
    # blast predicates
    qseqid = nt.qseqid
    sseqid = nt.sseqid
    pident = nt.pident
    length = nt.length
    mismatch = nt.mismatch
    gapopen = nt.gapopen
    qstart = nt.qstart
    qend = nt.qend
    sstart = nt.sstart
    send = nt.send
    evalue = nt.evalue
    bitscore = nt.bitscore
    # labels for sequences
    gb = nt.genbank_id
    epi_id = nt.epi_id
    # labels for strains
    strain_name = nt.strain_name
    barcode = nt.barcode
    epi_isolate = nt.epi_isolate
    has_segment = nt.has_segment
    # the local curated data
    ref_reason = nt.ref_reason
    country = nt.country
    country_name = nt.country_name
    state = nt.state
    subtype = nt.subtype
    ha_clade = nt.ha_clade
    na_clade = nt.na_clade
    date = nt.date
    time = nt.time
    file = nt.file
    host = nt.host
    encodes = nt.gene
    # -----------------------------------------------------------------------
    # gb/*  -- I need to start generalizing away from this, since this data
    # does not come only from genebank.
    # -----------------------------------------------------------------------
    feature_key = nt.feature_key
    gb_locus = nt.locus  # unique key
    gb_length = nt.length
    gb_strandedness = nt.strandedness
    gb_moltype = nt.moltype
    gb_topology = nt.topology
    gb_division = nt.division
    gb_update_date = nt.update_date
    gb_create_date = nt.create_date
    gb_definition = nt.definition
    gb_primary_accession = nt.primary_accession
    gb_accession_version = nt.accession_version
    gb_other_seqids = nt.other_seqids
    gb_source = nt.source
    gb_organism = nt.organism
    gb_taxonomy = nt.taxonomy
    gb_references = nt.references
    gb_sequence = nt.sequence
    # -----------------------------------------------------------------------
    # gb/feature/*
    # -----------------------------------------------------------------------
    # a set of features associated with this particular strain
    gb_key = nt.key  # feature type (source | gene | CDS | misc_feature)
    gb_location = nt.location
    gb_intervals = nt.intervals
    gb_operator = nt.operator
    # a set of qualifiers for this feature
    # in biopython, this is a list of
    # {'GBQualifier_value' 'GBQualifier_name'} dicts
    gb_codon_start = nt.codon_start
    gb_collection_date = nt.collection_date
    gb_country = nt.country
    gb_db_xref = nt.db_xref
    gb_gene = nt.gene
    gb_host = nt.host
    gb_isolation_source = nt.isolation_source
    gb_mol_type = nt.mol_type
    gb_note = nt.note
    gb_organism = nt.organism
    gb_product = nt.product
    gb_protein_id = nt.protein_id
    gb_serotype = nt.serotype
    gb_strain = nt.strain_name
    gb_transl_table = nt.transl_table
    gb_translation = nt.translation
