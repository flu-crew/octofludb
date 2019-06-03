from rdflib import (ConjunctiveGraph, URIRef, Literal)
import src.fasta as fasta
import src.geography as geog
import src.genbank as gb
from src.nomenclature import (P, O, nt)
from src.util import (replace, fixLookup, make_maybe_add)
import src.entrez as entrez
import re

def add_seq_meta_triples(g, meta):
  strain_uid = URIRef(str(meta["strain"]))

  g.add((strain_uid, P.has_segment, URIRef(meta["gb"])))
  g.add((strain_uid, P.is_a, O.strain))
  g.add((strain_uid, P.name, Literal(str(meta["strain"]))))

  maybe_add = make_maybe_add(g, meta, strain_uid)
  maybe_add(P.ref_reason, "ref_reason")
  maybe_add(P.subtype,    "subtype")
  maybe_add(P.country,    "country")
  maybe_add(P.state,      "state")
  maybe_add(P.ha_clade,   "ha_clade")
  maybe_add(P.date,       "date")

def label_strains(g:ConjunctiveGraph, filename:str, label:str)->None:
  with open(filename, "r") as f:
    for strain in (s.strip() for s in f.readlines()):
      uri = URIRef(strain.replace(" ", "_"))
      g.add((uri, P.tag, Literal(label)))
      g.add((uri, P.is_a, O.strain))
      g.add((uri, P.name, Literal(strain)))
  g.commit()

def load_influenza_na(g, filename):
  strain_pat = re.compile("A/[^()]+")
  with open(filename, "r") as f:
    field = dict()
    for row in f.readlines():
      els = row.split("\t") 
      field["gb"] = els[0]
      field["host"] = els[1]
      field["country"] = els[4]
      field["date"] = els[5]
      strain_match = re.search(strain_pat, els[7])
      if strain_match:
        field["strain"] = strain_match.group(0)

        strain_uid = URIRef(str(field["strain"]).replace(" ", "_"))

        maybe_add = make_maybe_add(g, field, strain_uid)

        g.add((strain_uid, P.has_segment, URIRef(field["gb"])))
        g.add((strain_uid, P.is_a, O.strain))
        g.add((strain_uid, P.name, Literal(str(field["strain"]))))

        maybe_add = make_maybe_add(g, field, strain_uid)
        maybe_add(P.host,    "host")
        maybe_add(P.country, "country")
        maybe_add(P.date,    "date")
  g.commit()

#  def load_reference_files(g, folder, uid):
#    for segment in ["m", "np", "ns", "pa", "pb1", "pb2"]:
#      filename = f'{folder}/{segment}_refs_aln_20180808.fasta'
#      segment_data = fasta.parse_internal_gene_reference(filename)
#      for (meta, seq) in segment_data:
#
#        # removing the CanadaNA case
#        meta = replace(meta, "country", "CanadaNA", "Canada")
#        # fix misspellings in names
#        meta = fixLookup(meta, "state", geog.STATE_MISPELLINGS, f=lambda x: x.lower())
#        # convert abbreviations to full names
#        meta = fixLookup(meta, "state", geog.STATE_ABBR, f=lambda x: x.upper())
#        # convert spaces to underscores in state names
#        meta = replace(meta, "state", " ", "_")
#
#        add_seq_meta_triples(g, meta, uid)
#
#    # collect the GenBank entries for all sequences and parse the data into the graph
#    gb_ids = [str(o) for s,p,o in g.triples((None, P.has_segment, None))]
#    for gb_meta in entrez.get_gbs(gb_ids):
#      gb.add_gb_meta_triples(g, gb_meta, uid)
#
#    g.commit()
