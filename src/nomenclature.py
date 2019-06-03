import itertools
from rdflib import Namespace
from rdflib.namespace import RDF, FOAF
from src.util import padDigit

ni = Namespace("http://github.com/arendsee/usda/ids/")
nt = Namespace("http://github.com/arendsee/usda/terms/")

def uidgen(base="_", pad=3, start=0):
  for i in itertools.count(0):
    yield ni.term(padDigit(base + str(i), pad))


class O:
  strain = nt.USDA_strain # unique key for the strain
  feature = nt.feature

class P:
  # standard semantic web predicates
  is_a = RDF.type
  name = FOAF.name
  knows = FOAF.knows
  # flu relations
  has_segment = nt.has_segment
  feature     = nt.feature
  tag        = nt.tag
  # the local curated data
  strain_alt = nt.USDA_strain_id_alt # alternative strain IDs
  gb         = nt.USDA_genbank_id # an optional unique key for the segment
  ref_reason = nt.USDA_ref_reason
  subtype    = nt.USDA_subtype
  segment    = nt.USDA_segment
  country    = nt.USDA_country
  state      = nt.USDA_state
  ha_clade   = nt.USDA_ha_clade
  date       = nt.USDA_date
  host       = nt.USDA_host
  # raw values from GenBank
  gb_locus             = nt.GBSeq_locus # unique key
  gb_length            = nt.GBSeq_length
  gb_strandedness      = nt.GBSeq_strandedness
  gb_moltype           = nt.GBSeq_moltype
  gb_topology          = nt.GBSeq_topology
  gb_division          = nt.GBSeq_division
  gb_update_date       = nt.GBSeq_update_date
  gb_create_date       = nt.GBSeq_create_date
  gb_definition        = nt.GBSeq_definition
  gb_primary_accession = nt.GBSeq_primary_accession
  gb_accession_version = nt.GBSeq_accession_version
  gb_other_seqids      = nt.GBSeq_other_seqids
  gb_source            = nt.GBSeq_source
  gb_organism          = nt.GBSeq_organism
  gb_taxonomy          = nt.GBSeq_taxonomy
  gb_references        = nt.GBSeq_references
  gb_sequence          = nt.GBSeq_sequence
  # a set of features associated with this particular strain
  gb_key       = nt.GBFeature_key # feature type (source | gene | CDS | misc_feature)
  gb_location  = nt.GBFeature_location
  gb_intervals = nt.GBFeature_intervals
  gb_operator  = nt.GBFeature_operator
  # a set of qualifiers for this feature
  # in biopython, this is a list of
  # {'GBQualifier_value' 'GBQualifier_name'} dicts
  gb_codon_start      = nt.GBFeature_codon_start
  gb_collection_date  = nt.GBFeature_collection_date
  gb_country          = nt.GBFeature_country
  gb_db_xref          = nt.GBFeature_db_xref
  gb_gene             = nt.GBFeature_gene
  gb_host             = nt.GBFeature_host
  gb_isolation_source = nt.GBFeature_isolation_source
  gb_mol_type         = nt.GBFeature_mol_type
  gb_note             = nt.GBFeature_note
  gb_organism         = nt.GBFeature_organism
  gb_product          = nt.GBFeature_product
  gb_protein_id       = nt.GBFeature_protein_id
  gb_segment          = nt.GBFeature_segment
  gb_serotype         = nt.GBFeature_serotype
  gb_strain           = nt.GBFeature_strain
  gb_transl_table     = nt.GBFeature_transl_table
  gb_translation      = nt.GBFeature_translation
