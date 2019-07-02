import parsec as p
import re
from collections import defaultdict, OrderedDict, namedtuple
from typing import List

import src.util as U

from src.nomenclature import P, O, make_uri, nt, make_literal, Literal

import src.domain.geography as geo
from src.domain.date import p_year, p_longyear, p_month, p_day, p_date
from src.domain.flu import (
    p_HA,
    p_NA,
    p_internal_gene,
    p_segment,
    p_segment_number,
    p_HANA,
    p_strain_obj,
    p_constellation,
)
from src.domain.identifier import (
    p_global_clade,
    p_A0,
    p_tosu,
    p_gisaid_isolate,
    p_strain,
    p_gb,
    p_gisaid_seqid,
)

from src.domain.animal import p_host
from src.domain.sequence import p_dnaseq, p_proseq

# parsec operators:
#  - "|" choice, any matching substring, even partially, is
#        consumed, thus "^" is normally what you want
#  - "^" try_choice, partial matches do not consume the stream
#  - "+" joint, keep the results of each match in a tuple
#  - ">>" compose, skips the lhs
#  - "<<" compose, skips the rhs
#  - "<" ends_with


def parse_match(parser, text):
    try:
        parser.parse_strict(text)
    except p.ParseError:
        return False
    return True


def wordset(words, label, f=lambda x: x.lower().replace(" ", "_")):
    """
  Create a log(n) parser for a set of n strings.
  @param "label" is a arbitrary name for the wordset that is used in error messages 
  @param "f" is a function used to convert matching strings in the wordset and text (e.g to match on lower case).
  """
    d = defaultdict(set)
    # divide words into sets of words of the same length
    # this allows exact matches against the sets
    for word in words:
        d[len(word)].update([f(word)])
    # Convert this to a list of (<length>, <set>) tuples reverse sorted by
    # length. The parser must search for longer strings first to avoid matches
    # against prefixes.
    d = sorted(d.items(), key=lambda x: x[0], reverse=True)

    @p.Parser
    def wordsetParser(text, index=0):
        for k, v in d:
            if f(text[index : (index + k)]) in v:
                return p.Value.success(index + k, text[index : (index + k)])
        return p.Value.failure(
            index, f'a term "{f(text[index:(index+k)])}" not in wordset {d}'
        )

    return wordsetParser


def regexWithin(regex: re.Pattern, context: p.Parser):
    @p.Parser
    def regexWithinParser(text, index=0):
        try:
            contextStr = context.parse(text[index:])
        except p.ParseError:
            return p.Value.failure(index, "Context not found")
        m = re.search(regex, contextStr)
        if m:
            return p.Value.success(index + len(contextStr), m.group(0))
        else:
            return p.Value.failure(index, "Could not match regex")

    return regexWithinParser


p_country = wordset(geo.COUNTRIES.keys(), label="country")
p_usa_state = wordset(
    words=list(geo.STATE_ABBR.values())
    + list(geo.STATE_ABBR.keys())
    + list(geo.STATE_MISPELLINGS.keys()),
    label="usa_state",
)

RelationSet = namedtuple("RelationSet", ["subjects", "relations", "objectify", "default"])

class RdfBuilder:
    def __init__(
        self,
        make_name={},
        relation_sets=[],  # (<set1>, <set2>)), both sets include names from the field parser,
        # with values in set1 being related to values in set2 by literal set2
        isa_map={},
        munge_map={},  # (<field>, <function>), munge <field> with <function> (e.g. to correct spelling)
        sub_builders=[],  # (<field>, <function>), create new triples from <field> using <function>,
        unknown_tag="unknown"
        # e.g., to parse host name from a strain name.
    ):
        self.make_name = make_name
        self.relation_sets = relation_sets
        self.munge_map = munge_map
        self.sub_builders = sub_builders
        self.isa_map = isa_map
        self.unknown_tag=unknown_tag
        # e.g., to parse host name from a strain name.

    def build(self, g, fieldss):
        """
        g is a 
        """
        
        for i, fields in enumerate(fieldss):
            self._buildOne(g, fields, idx=i)
        g.commit()

    def _buildOne(self, g, fields, idx, tag=None):
        # fields :: [(Tag, String)]

        # replace unknown tags
        for i in range(len(fields)):
            t,v = fields[i]
            if t is None:
                fields[i] = (self.unknown_tag, v)

        for i in range(len(fields)):
            t,v = fields[i]
            if t in self.munge_map:
                fields[i] = (t, self.munge_map[t](v))

        fieldSet = {x[0] for x in fields}

        # make URIs for each relation level
        for r in self.relation_sets:
            if not r.subjects & fieldSet:
                uri = "e" + str(idx) + "_" + str(hash(str(fields)))
                fields.append((r.default, uri))
                r.subjects.add(r.default)
                fieldSet.add(r.default)

        for k,v in fields:
            # make hierarchical relations
            for r in self.relation_sets:
                if k in r.subjects:
                    for k_,v_ in fields:
                        if k_ in r.relations:
                            g.add((make_uri(v), r.relations[k_], r.objectify[k_](v_)))

            # set foaf:name for this field
            if k in self.make_name:
                g.add((make_uri(v), P.name, Literal(self.make_name[k](v))))
            # define rdf:type of this field
            if k in self.isa_map:
                g.add((make_uri(v), P.is_a, self.isa_map[k]))
            # tag top-level fields
            if tag and k in self.relation_sets[0][0]:
                g.add((make_uri(v), P.tag, Literal(tag)))

        # build other stuff from the whole fields
        for builder in self.sub_builders:
            builder(g, fields)

def resolve(xss):
    """
    For now I resolve ambiguities by just taking the first matching parser.
    Eventually I can replace this with real context-dependent choices. 
    """
    return ([(x[0][0], x[0][1]) for x in xs] for xs in xss)

def groupSortToOrderedDict(xs):
    """
    condense :: [(Key, Val)] -> {Key : [Val]} 
    """
    xs.sorted()
    ys = [(xs[0][0], [xs[0][1]])]
    for k,v in xs[1:]:
      if k == ys[-1][0]:
        ys[-1][1].append(k)
      else:
        ys.append((k, [v]))
    
    return OrderedDict(ys)


fastaHeaderFieldParsers = (
    # strain ids
    ("A0", p_A0),
    ("tosu", p_tosu),
    ("gisaid_isolate", p_gisaid_isolate),
    ("strain", p_strain),
    # sequence ids
    ("gb", p_gb),
    ("gisaid_seqid", p_gisaid_seqid),
    # other flu info
    ("global_clade", p_global_clade),
    ("constellation", p_constellation),
    #
    ("host", p_host),
    ("date", p_date.parsecmap(str)),
    ("subtype", p_HANA),
    ("segment_name", p_segment),
    ("state", p_usa_state),  # Pennslyvania (PA) conflicts with the segment PA
    ("country", p_country),  # country Turkey conflicts with the host
    ("segment_number", p_segment_number),
    ("proseq", p_proseq),
    ("dnaseq", p_dnaseq),
)

def guess_fields(fieldss: List[List[str]], parserSet=fastaHeaderFieldParsers):
    for fields in fieldss:
        xs = list()
        for field in fields:
            field_results = list()
            for (name, parser) in parserSet:
                try:
                    s = parser.parse_strict(field)
                    field_results.append((name, s))
                except p.ParseError:
                    next
            if not field_results:
                field_results = [(None, field)]
            xs.append(field_results)
        yield xs
