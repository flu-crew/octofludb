import itertools
from rdflib import (Namespace, URIRef)
from rdflib.namespace import RDF, FOAF
from src.util import padDigit

ni = Namespace("https://github.com/arendsee/flucrew/id/")
nt = Namespace("https://github.com/arendsee/flucrew/term/")
ne = Namespace("https://github.com/arendsee/flucrew/event/")

def uidgen(base="_", pad=3, start=0):
  base = base.replace(" ", "_")
  for i in itertools.count(0):
    yield ni.term(padDigit(base + str(i), pad))

def make_uri(x):
  return(URIRef(str(x).replace(" ", "_")))


class O:
  strain = nt.strain_id # unique key for the strain
  gb = nt.genbank_id
  barcode = nt.barcode
  gisaid = nt.gisaid
  feature = nt.feature
  complete_genome = nt.complete_genome
  event = nt.event
  dnamd5 = nt.dna_md5
  dnaseq = nt.dna_sequence
  protein_sequence = nt.protein_sequence
  protein_md5 = nt.protein_md5

class P:
  # standard semantic web predicates
  is_a = RDF.type
  name = FOAF.name
  knows = FOAF.knows
  related_to = nt.related_to
  xref = nt.xref 
  # flu relations
  has_segment = nt.has_segment
  feature     = nt.feature
  tag         = nt.tag
  dnaseq = nt.dna_sequence
  proseq = nt.protein_sequence
  dnamd5 = nt.dna_md5
  aamd5 = nt.aa_md5
  protein_md5 = nt.protein_md5
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
  # the local curated data
  strain_alt = nt.strain_id_alt # alternative strain IDs
  gb         = nt.genbank_id # an optional unique key for the segment
  ref_reason = nt.ref_reason
  subtype    = nt.subtype
  segment    = nt.segment
  country    = nt.country
  state      = nt.state
  ha_clade   = nt.ha_clade
  date       = nt.date
  host       = nt.host
  encodes    = nt.encodes
  # ----------------------------------------
  # gb/*
  # ----------------------------------------
  gb_locus             = nt.locus # unique key
  gb_length            = nt.length
  gb_strandedness      = nt.strandedness
  gb_moltype           = nt.moltype
  gb_topology          = nt.topology
  gb_division          = nt.division
  gb_update_date       = nt.update_date
  gb_create_date       = nt.create_date
  gb_definition        = nt.definition
  gb_primary_accession = nt.primary_accession
  gb_accession_version = nt.accession_version
  gb_other_seqids      = nt.other_seqids
  gb_source            = nt.source
  gb_organism          = nt.organism
  gb_taxonomy          = nt.taxonomy
  gb_references        = nt.references
  gb_sequence          = nt.sequence
  # ----------------------------------------
  # gb/feature/*
  # ----------------------------------------
  # a set of features associated with this particular strain
  gb_key       = nt.key # feature type (source | gene | CDS | misc_feature)
  gb_location  = nt.location
  gb_intervals = nt.intervals
  gb_operator  = nt.operator
  # a set of qualifiers for this feature
  # in biopython, this is a list of
  # {'GBQualifier_value' 'GBQualifier_name'} dicts
  gb_codon_start      = nt.codon_start
  gb_collection_date  = nt.collection_date
  gb_country          = nt.country
  gb_db_xref          = nt.db_xref
  gb_gene             = nt.gene
  gb_host             = nt.host
  gb_isolation_source = nt.isolation_source
  gb_mol_type         = nt.mol_type
  gb_note             = nt.note
  gb_organism         = nt.organism
  gb_product          = nt.product
  gb_protein_id       = nt.protein_id
  gb_segment          = nt.segment
  gb_serotype         = nt.serotype
  gb_strain           = nt.strain
  gb_transl_table     = nt.transl_table
  gb_translation      = nt.translation
