import parsec as p
import re
import rdflib
import sys
from collections import defaultdict, OrderedDict, namedtuple
from typing import List

import src.util as U

from src.nomenclature import P, O, make_uri, make_literal, make_property, make_usa_state_uri

import src.domain.geography as geo
from src.domain.date import p_year, p_longyear, p_month, p_day, p_date, p_any_date
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


def splitMatchFirst(psr: p.Parser, splitStr: str, text: str):
    """
    Rethink whether this is needed ...
    """
    fields = text.split(splitStr)
    for field in fields:
        try:
            return psr.parse_strict(field)
        except:
            continue
    return None


p_usa_state = wordset(
    words=list(geo.STATE_NAME2ABBR.values()) + list(geo.STATE_NAME2ABBR.keys()),
    label="usa_state",
)


@p.Parser
def p_country(text, index=0):
    if geo.country_to_code(text):
        return p.Value.success(index + len(text), text)
    else:
        return p.Value.failure(
            index, "I do not currenlty recognize this country, take it up with the UN"
        )


RelationSet = namedtuple(
    "RelationSet", ["subjects", "relations", "generators", "objectifier", "default"]
)


class RdfBuilder:
    def __init__(
        self,
        relation_sets=[],  # (<set1>, <set2>)), both sets include names from the field parser,
        munge_map={},  # (<field>, <function>), munge <field> with <function> (e.g. to correct spelling)
        sub_builders=[],  # (<field>, <function>), create new triples from <field> using <function>,
        unknown_tag="unknown",
        tag=None,
    ):
        self.relation_sets = relation_sets
        self.munge_map = munge_map
        self.sub_builders = sub_builders
        self.unknown_tag = unknown_tag
        self.tag = tag

    def build(self, g, fieldss):
        """
        g is a 
        """

        for i, fields in enumerate(fieldss):
            self._buildOne(g, fields, idx=i)
        g.commit()

    def _buildOne(self, g, fields, idx):
        # fields :: [(Tag, String)]

        # replace unknown tags
        for i in range(len(fields)):
            t, v = fields[i]
            if t is None:
                fields[i] = (self.unknown_tag, v)

        for i in range(len(fields)):
            t, v = fields[i]
            if t in self.munge_map:
                fields[i] = (t, self.munge_map[t](v))

        fieldSet = {x[0] for x in fields}

        # make URIs for each relation level
        for r in self.relation_sets:
            #  print(f"> r.subjects: {r.subjects}  | fieldSet: {fieldSet}")
            genfield = set(r.generators.keys()) & fieldSet
            #  print(f"genfield: {genfield}")
            if genfield:
                for (k, v) in fields:
                    #  print(f" k={k} v={v}")
                    if k in genfield:
                        default = r.generators[k][0]
                        uri = r.generators[k][1](v)
                        fields.append((default, uri))
                        r.subjects.add(default)
                        fieldSet.add(default)
            if not r.subjects:
                uri = "e" + str(idx) + "_" + str(hash(str(fields)))
                default = r.default
                fields.append((r.default, uri))
                r.subjects.add(r.default)
                fieldSet.add(r.default)

        for k, v in fields:
            # make hierarchical relations
            for r in self.relation_sets:
                if k in r.subjects:
                    uri = make_uri(v)
                    if not isinstance(v, rdflib.term.URIRef):
                        g.add((uri, make_property(k), make_literal(v)))
                    for k_, v_ in fields:
                        if k_ in r.relations:
                            g.add((uri, r.relations[k_], r.objectifier[k_](v_)))

            # tag top-level fields
            if self.tag and k in self.relation_sets[0][0]:
                g.add((make_uri(v), P.tag, make_literal(self.tag, False)))

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
    for k, v in xs[1:]:
        if k == ys[-1][0]:
            ys[-1][1].append(k)
        else:
            ys.append((k, [v]))

    return OrderedDict(ys)

def maybe_parse(p, x):
    try:
        return p.parse_strict(x)
    except:
        return None


def guess_fields(fieldss: List[List[str]], parserSet=None):
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
