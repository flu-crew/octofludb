from src.nomenclature import (uidgen, P, O, nt)
from src.util import (rmNone, make_maybe_add)
from rdflib import (URIRef, Literal)
from hashlib import md5
import sys

def add_gb_meta_triples(g, gb_meta):
  gid = URIRef(str(gb_meta["GBSeq_locus"]))

  g.add((gid, P.name, Literal(gb_meta["GBSeq_locus"])))

  maybe_add = make_maybe_add(g, gb_meta, gid)
  maybe_add(P.gb_length,            "GBSeq_length")
  maybe_add(P.gb_strandedness,      "GBSeq_strandedness")
  maybe_add(P.gb_moltype,           "GBSeq_moltype")
  maybe_add(P.gb_topology,          "GBSeq_topology")
  maybe_add(P.gb_division,          "GBSeq_division")
  maybe_add(P.gb_update_date,       "GBSeq_update_date")
  maybe_add(P.gb_create_date,       "GBSeq_create_date")
  maybe_add(P.gb_definition,        "GBSeq_definition")
  maybe_add(P.gb_primary_accession, "GBSeq_primary_accession")
  maybe_add(P.gb_accession_version, "GBSeq_accession_version")
  maybe_add(P.gb_source,            "GBSeq_source")
  maybe_add(P.gb_organism,          "GBSeq_organism")
  maybe_add(P.gb_taxonomy,          "GBSeq_taxonomy")

  seq = gb_meta["GBSeq_sequence"].upper()
  seqmd5 = md5()
  seqmd5.update(bytes(seq.encode("ascii")))
  g.add((gid, P.dnaseq, Literal(seq)))
  g.add((gid, P.dnamd5, Literal(seqmd5.hexdigest())))

  igen = uidgen(base=gb_meta["GBSeq_locus"] + "_feat_")
  for feat in gb_meta["GBSeq_feature-table"]:
    fid = next(igen)
    g.add((gid, P.feature, fid))
    g.add((fid, P.is_a, O.feature))
    g.add((fid, P.is_a, nt.term(feat["GBFeature_key"])))

    maybe_add = make_maybe_add(g, feat, fid)
    maybe_add(P.gb_location, "GBFeature_location")
    #  maybe_add(P.gb_key, "GBFeature_intervals") # for laters

    if "GBFeature_quals" in feat:
      for qual in feat["GBFeature_quals"]:
        if qual["GBQualifier_name"] == "translation":
          aaseq = qual["GBQualifier_value"]
          aaseqmd5 = md5()
          aaseqmd5.update(bytes(seq.encode("ascii")))
          g.add((fid, P.proseq, Literal(aaseq)))
          g.add((fid, P.aamd5, Literal(aaseqmd5.hexdigest())))
        else:
          try:
            g.add((
              fid,
              nt.term(qual["GBQualifier_name"]),
              Literal(qual["GBQualifier_value"])
            ))
          except KeyError:
            print(f'In {gb_meta["GBSeq_locus"]}: Could not load: {str(qual)}', file=sys.stderr)
