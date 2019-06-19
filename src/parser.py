import parsec as p
import re
from collections import defaultdict
from typing import List

from src.util import concat
from src.util import padDigit 
from src.util import rmNone

from src.nomenclature import (P, O, make_uri)

import src.domain.geography as geo
from src.domain.date import (p_year, p_longyear, p_month, p_day, p_date)
from src.domain.flu import (p_HA, p_NA, p_internal_gene, p_segment, p_segment_number, p_HANA, p_strain_obj, p_constellation)
from src.domain.identifier import (p_global_clade, p_A0, p_tosu, p_gisaid_isolate, p_strain, p_gb, p_gisaid_seqid)

from src.domain.animal import (p_host)
from src.domain.sequence import (p_dnaseq, p_proseq)

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
    for k,v in d:
      if f(text[index:(index+k)]) in v:
        return p.Value.success(index+k, text[index:(index+k)])
    return p.Value.failure(index, f'a term "{f(text[index:(index+k)])}" not in wordset {d}')
  return wordsetParser

def regexWithin(regex:re.Pattern, context:p.Parser):
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
    words = list(geo.STATE_ABBR.values()) +
            list(geo.STATE_ABBR.keys()) +
            list(geo.STATE_MISPELLINGS.keys()) +
            ["USA", "United States"], # may be used when state is not available 
    label = "usa_state"
  )

fastaHeaderFieldParsers = (
    # strain ids
    ("A0",             p_A0),
    ("tosu",           p_tosu),
    ("gisaid_isolate", p_gisaid_isolate),
    ("strain",         p_strain),
    # sequence ids
    ("gb",             p_gb),
    ("gisaid_seqid",   p_gisaid_seqid),
    # other flu info
    ("global_clade",   p_global_clade),
    ("constellation",  p_constellation),
    #
    ("host",           p_host),
    ("date",           p_date.parsecmap(str)),
    ("subtype",        p_HANA),
    ("segment_name",   p_segment),
    ("state",          p_usa_state), # Pennslyvania (PA) conflicts with the segment PA
    ("country",        p_country),   # country Turkey conflicts with the host
    ("segment_number", p_segment_number),
    ("proseq",         p_proseq),
    ("dnaseq",         p_dnaseq)
  )

def resolve(xss):
  """
  For now I resolve ambiguities by just taking the first matching parser.
  Eventually I can replace this with real context-dependent choices. 
  """
  return ([(x[0][0], x[0][1]) for x in xs] for xs in xss)

def guess_fields(fieldss:List[List[str]], parserSet=fastaHeaderFieldParsers):
  for fields in fieldss:
    xs = list()
    for field in fields:
      field_results = list()
      for (name,parser) in parserSet:
        try:
          s = parser.parse_strict(field)
          field_results.append((name, s))
        except p.ParseError:
          next
      if not field_results:
        field_results = [(None, field)]
      xs.append(field_results)
    yield xs
