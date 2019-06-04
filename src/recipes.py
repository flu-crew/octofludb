import sys
from rdflib import (ConjunctiveGraph, URIRef, Literal)
import src.fasta as fasta
import src.geography as geog
import src.genbank as gb
import src.flu as flu
import src.date as date
from src.nomenclature import (P, O, nt, ne)
from src.util import (replace, fixLookup, make_maybe_add)
import src.entrez as entrez
import re
import pandas as pd

STRAIN_PAT = re.compile("[ABCD]/[^()]+")
A0_PAT = re.compile("A0\d{7}") #e.g. A01104095
GENBANK_PAT = re.compile("[A-Z][A-Z]?\d{5,7}")

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

def tag_strains(g:ConjunctiveGraph, filename:str, tag:str)->None:
  with open(filename, "r") as f:
    for strain in (s.strip() for s in f.readlines()):
      uri = URIRef(strain.replace(" ", "_"))
      g.add((uri, P.tag, Literal(tag)))
      g.add((uri, P.is_a, O.strain))
      g.add((uri, P.name, Literal(strain)))
  g.commit()

def tag_gb(g:ConjunctiveGraph, filename:str, tag:str)->None:
  with open(filename, "r") as f:
    for gb in (s.strip() for s in f.readlines()):
      uri = URIRef(gb.replace(" ", "_"))
      g.add((uri, P.tag, Literal(tag)))
      g.add((uri, P.is_a, O.gb))
      g.add((uri, P.name, Literal(gb)))
  g.commit()

def load_factor(
  g:ConjunctiveGraph,
  table_filename:str,
  relation:str,
  key_type:str="strain"
)->None:
  if key_type == "strain":
    o = O.strain 
  elif key_type == "A0":
    o = O.a0
  elif key_type == "gb":
    o = O.gb
  else:
    sys.exit("please choose key_type from strain, A0, and gb")
  with open(table_filename, "r") as f:
    for (key,val) in ((k.strip(),v.strip()) for k,v in f.readlines().split("\t")):
      uri = URIRef(key.replace(" ", "_"))
      g.add((uri, nt.term(relation), Literal(tag)))
      g.add((uri, nt.is_a, o))
  g.commit()

def infer_type(x):
  x_is_a = None
  if re.fullmatch(STRAIN_PAT, x):
    x_is_a = O.strain
  elif re.fullmatch(A0_PAT, x):
    x_is_a = O.a0
  elif re.fullmatch(GENBANK_PAT, x):
    x_is_a = O.gb
  return x_is_a

def make_literal(x):
  try:
    # Can x be a date?
    x_lit = Literal(str(date.p_date.parse(x)), datatype=XSD.date)
  except:
    # If not, then make it a normal literal
    x_lit = Literal(x) 
  return(x_lit)

def load_excel(g:ConjunctiveGraph, filename:str, event=None)->None:
  d = pd.read_excel(filename)

  if event:
    event_uri = ne.term(event) 
    g.add((event_uri, P.is_a, O.event))
    g.add((event_uri, P.name, Literal(event)))

  for i in range(d.shape[0]):
    s = d.iloc[i][0] # subject - the id from the table's key column
    # the subject URI cannot have spaces
    uri = URIRef(s.lower().replace(" ", "_"))

    if event:
      g.add((event_uri, P.related_to, uri))

    # associate the ID with its name
    g.add((uri, P.name, Literal(s)))

    # try to determine the type of the ID (e.g., strain, genebank or A0)
    # if successful, add a triple linking the id to its type
    s_type = infer_type(s)
    if s_type != None:
      g.add((uri, P.is_a, s_type))

    # associate the ID with each element in the row with column names as predicates
    for j in range(1, d.shape[1]):
      p = d.columns[j] # predicate - the column name
      o = d.iloc[i][j] # object - the value in the cell

      # the predict shouldn't have spaces and I convert to lower case to avoid
      # case mismatches in lookups
      p = p.lower().replace(" ", "_")

      g.add((uri, nt.term(p), make_literal(o)))

  g.commit()


def load_influenza_na(g:ConjunctiveGraph, filename:str)->None:
  with open(filename, "r") as f:
    field = dict()
    for row in f.readlines():
      els = row.split("\t") 
      try:
        field["gb"] = els[0]
        field["host"] = els[1]
        field["segment"] = els[2]
        field["country"] = els[4]
        field["date"] = els[5]
        is_complete = els[10].strip() == "c"
      except IndexError:
        print(f'Expected 11 columns, found only {len(els)}. This is unexpected and a little frightening.', file=sys.stderr)

      gb_uid = URIRef(field["gb"])
      g.add((gb_uid, P.is_a, O.gb))
      g.add((gb_uid, P.segment, Literal(field["segment"])))
      g.add((gb_uid, P.encodes, Literal(flu.SEGMENT[int(els[2])-1])))
      if is_complete:
        g.add((gb_uid, P.tag, Literal("complete_genome")))

      # Skip entries where no strain name can be extracted
      # * A good column 7 should look like this:
      #     Influenza A virus (A/Arequipa/FLU3833/2006(H3))
      #     Influenza B virus (B/Jiangsu/10e9/2003)
      # * Here are a few pathological ones:
      #     Influenza A virus
      #     Influenza A virus (swine/Finistere/127/99(H3N2))
      #     Influenza A virus (St Jude H5N1 influenza seed virus 163222)
      #     Influenza A virus H3N2
      #     unidentified influenza virus
      # * In the current database (06/04/2019) 541/712177 entries are pathological
      strain_match = re.search(STRAIN_PAT, els[7])
      if strain_match:
        strain = strain_match.group(0)

        strain_uid = URIRef(strain.replace(" ", "_"))
        maybe_add = make_maybe_add(g, field, strain_uid)
        g.add((strain_uid, P.has_segment, gb_uid))
        g.add((strain_uid, P.is_a, O.strain))
        g.add((strain_uid, P.name, Literal(strain)))

        a0_match = re.search(A0_PAT, strain)
        if a0_match:
          a0_name = a0_match.group(0)
          a0_uid = URIRef(a0_name)
          g.add((strain_uid, P.xref, a0_uid))
          g.add((a0_uid, P.xref, strain_uid))
          g.add((a0_uid, P.is_a, O.a0))
          g.add((a0_uid, P.name, Literal(a0_uid)))

        maybe_add = make_maybe_add(g, field, strain_uid)
        maybe_add(P.host,    "host")
        maybe_add(P.country, "country")
        maybe_add(P.date,    "date")
      else:
        print(f'could not parse strain: {"|".join(els)}', file=sys.stderr, end="")
  g.commit()
