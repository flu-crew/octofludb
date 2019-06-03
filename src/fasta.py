from src.strain import (p_strain)
from src.tokens import *
from src.geography import (p_state)
from src.date import (p_date, p_longyear)

DNA_REGEX = re.compile("[ATGC_RYSWKMBDHVN-]+", re.IGNORECASE)
def make_p_fasta(p_header, alphabet=DNA_REGEX):
  p_seq = p.sepBy1(p.regex(alphabet), sep=p.string("\n")).parsecmap(concat)
  p_entry = p_header + p_seq 
  p_fasta = p.many1(p_entry)
  return(p_fasta)

@p.generate
def _parse_internal_gene_reference_header():
  result = dict()
  #  ">pdm_TRIGavOrigin|FJ969516|A/California/04/2009|H1N1"
  yield p.string(">")
  # The first three columns are well-behaved
  result["ref_reason"] = yield p.regex("[^|]+") << p.string("|")
  result["gb"] = yield p_gb << p.string("|")
  result["strain"] = yield p_strain << p.string("|")
  # These all match HANA except for a few "unknown" and "mixed" cases 
  result["subtype"] = yield (p_HANA ^ p.string("unknown") ^ p.string("mixed"))
  yield p.optional(p.string("|"))
  # Get the segment
  result["segment"] = yield p.optional(p_segment)
  yield p.optional(p.string("|"))
  # Well-behaved North American countries ... (except the 2009 again)
  # NOTE: the CanadaNA case shows up here, I will remove it below
  result["country"] = yield p.optional(p.regex("USA|CanadaNA|Canada") << p.string("|"))
  yield p.optional(p.string("|"))
  # The next 4 fields may or may not be present, but are in the same order and
  # can be unambiguously parsed out.
  result["state"] = yield p.optional(p_state << p.string("|"))
  yield p.optional(p.string("|"))
  result["ha_clade"] = yield p.optional(p_global << p.string("|"))
  yield p.optional(p.string("|"))
  result["date"] = yield p.optional(p_date ^ p_longyear)
  yield p.spaces()
  return(result)

def parse_internal_gene_reference(filename):
  p_fasta = make_p_fasta(_parse_internal_gene_reference_header)
  with open(filename, "r") as f:
    return(p_fasta.parse(f.read()))
