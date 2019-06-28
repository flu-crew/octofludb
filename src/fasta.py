import parsec as p

from src.parser import guess_fields, resolve, RdfBuilder, RelationSet
import src.util as U
from src.nomenclature import P, O, make_uri, nt, make_literal, URIRef, Literal


def parse_fasta(filename, sep="|"):
    p_header = p.string(">") >> p.regex(".*") << p.spaces()
    p_seq = (
        p.sepBy1(p.regex("[^>\n]*"), sep=p.regex("[\r\n\t ]+")).parsecmap(U.concat)
        << p.spaces()
    )
    p_entry = p_header + p_seq
    p_fasta = p.many1(p_entry)

    with open(filename, "r") as f:
        entries = p_fasta.parse(f.read())
        row = (h.split(sep) + [q] for (h, q) in entries)
        return resolve(guess_fields(row))

def print_fasta(fields):
    for entry in fields:
        header = "|".join(
            (
                f"{str(entry[i][0])}={str(entry[i][1])}"
                for i in range(len(entry) - 1)
            )
        )
        seq = entry[-1][1]
        print(">" + header)
        print(seq)

def graph_fasta(g, fieldss):
  # - Create foaf:name links as needed, munging as needed
  fastaName = {
      "A0": U.upper,
      "tosu": U.upper,
      "gb": U.upper,
      "strain": U.compose(U.strip, U.underscore),
      "gisaid_seqid": U.upper,
  }

  # - If no strain ID exists, create a new one
  # - Link strain ID to each strain property
  # - Link segment ID to each segment property
  fastaRelationSets = [
      RelationSet (
          {"strain", "A0", "tosu", "gisaid_isolate"},
          {
              "global_clade" : nt.global_clade,
              "constellation" : nt.constellation,
              "host" : nt.host,
              "date" : nt.date,
              "state" : nt.state,
              "country" : nt.country,
              "subtype" : nt.subtype,
              "gb" : P.segment,
              "gisaid_seqid" : P.segment,
              "unknown_sequence" : P.unknown_sequence,
          },
          {
              "global_clade" : Literal,
              "constellation" : Literal,
              "host" : Literal,
              "date" : make_literal, 
              "state" : Literal,
              "country" : Literal,
              "subtype" : Literal,
              "gb" : URIRef,
              "gisaid_seqid" : URIRef,
              "unknown_sequence" : URIRef,
          },
          "unknown_strain",
      ),
      RelationSet (
          {"gb", "gisaid_seqid"},
          {
              "segment_name" : nt.segment_name,
              "segment_number" : nt.segment_number,
              "proseq" : O.proseq,
              "dnaseq" : O.dnaseq,
              "unknown" : O.unknown_unknown
          },
          {
              "segment_name" : Literal,
              "segment_number" : Literal,
              "proseq" : Literal,
              "dnaseq" : Literal,
              "unknown" : Literal
          },
          "unknown_sequence"
      ),
  ]

  # - Specify is_a relationships
  fastaIsaMap = {
      "A0": O.a0,
      "tosu": O.tosu,
      "gisaid_isolate": O.gisaid_isolate,
      "strain": O.strain,
      "gb": O.gb,
      "gisaid_seqid": O.gisaid_seqid,
      "unknown_strain": O.unknown_strain,
      "unknown_sequence": O.unknown_sequence,
  }

  fastaMungeMap = {"date": make_literal, "host": U.lower}

  # - Generate additional triples
  fastaGenerateAdditional = []

  fluRdfBuilder = RdfBuilder(
      make_name=fastaName,
      relation_sets=fastaRelationSets,
      isa_map=fastaIsaMap,
      munge_map=fastaMungeMap,
      sub_builders=fastaGenerateAdditional,
      unknown_tag="unknown"
  )

  fluRdfBuilder.build(g, fieldss)
  g.commit()
