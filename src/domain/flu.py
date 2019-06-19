import parsec as p
from src.domain.date import (p_year)
from src.domain.identifier import (p_A0)
from src.util import (rmNone, concat)

# the 8 segments of the flu genome (order matters)
SEGMENT = ["PB2", "PB1", "PA", "HA", "NP", "NA", "M", "NS1"]

p_HA = p.regex('H\d+') ^ p.regex('pdmH\d+')
p_NA = p.regex('N\d+')
p_internal_gene = p.regex("PB2|PB1|PA|NP|M|NS1")
p_segment = p_internal_gene | p_HA | p_NA
p_HANA = p.regex("H\d+N\d+")
p_constellation = p.regex("[TPV]{6}")
p_segment_number = p.regex("[1-8]")

class Strain:
  def __init__(self, flutype=None, subtype=None, host=None, place=None, ident=None, year=None, raw=None):
    self.flutype = flutype
    self.host = host
    self.place = place
    self.ident = ident
    self.year = year
    self.subtype = subtype
    try:
      self.a0 = p_A0.parse(self.ident)
    except:
      self.a0 = None

  def getHost(self):
    if self.host:
      return(self.host)
    else:
      return("human")

  def __str__(self):
    fields = ["A", self.host, self.place, self.ident, self.year]
    return("/".join(rmNone(fields)))

p_strain_field = p.regex("[^|/\n\t]+")

# A/Alaska/1935
# A/Alaska/1935(H1N1)
# A/New Jersey/1940
# A/Denver/1957
@p.generate
def p_s3():
  flutype = yield p.regex("[ABC]") << p.string("/")
  place = yield p_strain_field << p.string("/")
  year = yield p_year
  subtype = yield p.optional(p.string("(") >> p_HANA << p.string(")"))
  return(Strain(flutype=flutype, place=place, year=year, subtype=subtype))

# A/Baylor/11735/1982
# A/Berkeley/1/66
# A/California/NHRC-OID_SAR10587N/2018
# A/District of Columbia/WRAIR1753P/2010(H3N2)
# A/District_Of_Columbia/03/2014
@p.generate
def p_s4():
  flutype = yield p.regex("[ABC]") << p.string("/")
  place = yield p_strain_field << p.string("/")
  ident = yield p_strain_field << p.string("/")
  year = yield p_year
  subtype = yield p.optional(p.string("(") >> p_HANA << p.string(")"))
  return(Strain(flutype=flutype, place=place, year=year, ident=ident, subtype=subtype))

# A/Swine/Iowa/533/99
# A/swine/Iowa/3421/1990
# A/swine/Nebraska/00722/2005_mixed_
# A/swine/Ontario/55383/04
# A/swine/Oklahoma/A01785279/2017
@p.generate
def p_s5():
  flutype = yield p.regex("[ABC]") << p.string("/")
  host = yield p_strain_field << p.string("/")
  place = yield p_strain_field << p.string("/")
  ident = yield p_strain_field << p.string("/")
  year = yield p_year
  subtype = yield p.optional(p.string("(") >> p_HANA << p.string(")"))
  return(Strain(flutype=flutype, host=host, place=place, year=year, ident=ident, subtype=subtype))

p_strain_obj = p_s5 ^ p_s4 ^ p_s3
