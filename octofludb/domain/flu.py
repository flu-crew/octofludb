import parsec as p
import re
from octofludb.domain.date import p_year
from octofludb.domain.identifier import p_A0
from octofludb.parser import wordset
from octofludb.util import rmNone, concat

# the 8 segments of the flu genome (order matters)
SEGMENT = ["PB2", "PB1", "PA", "HA", "NP", "NA", "M", "NS"]

p_HA = p.regex("H\d+") ^ p.regex("pdmH\d+")
p_NA = p.regex("N\d+") ^ p.regex("N\d+pdm")

p_ns = p.regex("NS1?").parsecmap(lambda x: "NS")
p_m = p.regex("M[P1]?").parsecmap(lambda x: "M")
p_internal_gene = p.regex("PB2|PB1|PA|NP") ^ p_ns ^ p_m

p_segment = p_internal_gene ^ p.string("HA") ^ p.string("NA")
p_constellation = p.regex("[TPVHX-]{6}|MIXED")
p_segment_number = p.regex("[1-8]")
p_segment_subtype = p_segment ^ p_HA ^ p_NA


@p.generate
def p_subtype_unmixed():
    yield p.regex("(A *\/ *)?")
    ha = yield p_HA
    host = yield p.regex("(hu|sw|av)?")
    na = yield p_NA
    v = yield p.regex("(v)?")
    return ha + host + na + v


p_subtype_mixed = p.regex("mixed", re.I).parsecmap(lambda x: "mixed")
p_subtype = p_subtype_mixed ^ p_subtype_unmixed


def mapreplace(x, pattern, replace):
    if x == pattern:
        return replace
    else:
        return x


p_h1_clade = wordset(
    [
        "alpha",
        "beta",
        "delta1",
        "delta1a",
        "delta1b",
        "delta2",
        "gamma",
        "gamma2",
        "gamma2-beta-like",
        "gamma2_beta_like",
        "pandemic",
        "pdm",
        "pdmH1",
        "human-delta",
        "huVac",
        "predelta",
    ],
    label="h1_clade",
)
p_h3_clade = wordset(
    [
        "2010.1",
        "2010.2",
        "Cluster_I",
        "Cluster_II",
        "Cluster_III",
        "Cluster_IV",
        "Cluster_IVA",
        "Cluster_IVB",
        "Cluster_IVC",
        "Cluster_IVD",
        "Cluster_IVE",
        "Cluster_IVF",
        "I",
        "II",
        "III",
        "IV",
        "IV-A",
        "IV-B",
        "IV-C",
        "IV-D",
        "IV-E",
        "IV-F",
        "huVac",
        "human-like_2010.1",
        "human-like_2010.2",
        "human-like_2016",
    ],
    label="h3_clade",
)
p_n1_clade = wordset(
    ["Human_seasonal", "huVac", "Classical", "Pandemic", "MN99"], label="n1_clade"
)
p_n2_clade = wordset(
    [
        "Human_N2",
        "2016",
        "Human-like",
        "1998",
        "1998A",
        "98A",
        "98A1",
        "98A_1",
        "98A2",
        "98A_2",
        "1998B",
        "98B",
        "98B1",
        "98B_1",
        "98B2",
        "98B_2",
        "2002",
        "2002A",
        "02A1",
        "02A2",
        "2002B",
        "02B1",
        "02B2",
        "TX98",
    ],
    label="n3_clade",
)

p_internal_gene_clade = wordset(
    ["PDM", "TRIG", "LAIV"], label="internal_gene_clade"
).parsecmap(lambda x: x.upper())


class Strain:
    def __init__(
        self,
        flutype=None,
        subtype=None,
        host=None,
        place=None,
        ident=None,
        year=None,
        raw=None,
    ):
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
            return self.host
        else:
            return "human"

    def __str__(self):
        fields = ["A", self.host, self.place, self.ident, self.year]
        return "/".join(rmNone(fields))


p_strain_field = p.regex("[^|/\n\t]+")

# A/Alaska/1935
# A/Alaska/1935(H1N1)
# A/New Jersey/1940
# A/Denver/1957
@p.generate
def p_s3():
    flutype = yield p.regex("[ABCD]") << p.string("/")
    place = yield p_strain_field << p.string("/")
    year = yield p_year
    subtype = yield p.optional(p.string("(") >> p_subtype << p.string(")"))
    return Strain(flutype=flutype, place=place, year=year, subtype=subtype)


# A/Baylor/11735/1982
# A/Berkeley/1/66
# A/California/NHRC-OID_SAR10587N/2018
# A/District of Columbia/WRAIR1753P/2010(H3N2)
# A/District_Of_Columbia/03/2014
@p.generate
def p_s4():
    flutype = yield p.regex("[ABCD]") << p.string("/")
    place = yield p_strain_field << p.string("/")
    ident = yield p_strain_field << p.string("/")
    year = yield p_year
    subtype = yield p.optional(p.string("(") >> p_subtype << p.string(")"))
    return Strain(flutype=flutype, place=place, year=year, ident=ident, subtype=subtype)


# A/Swine/Iowa/533/99
# A/swine/Iowa/3421/1990
# A/swine/Nebraska/00722/2005_mixed_
# A/swine/Ontario/55383/04
# A/swine/Oklahoma/A01785279/2017
@p.generate
def p_s5():
    flutype = yield p.regex("[ABCD]") << p.string("/")
    host = yield p_strain_field << p.string("/")
    place = yield p_strain_field << p.string("/")
    ident = yield p_strain_field << p.string("/")
    year = yield p_year
    subtype = yield p.optional(p.string("(") >> p_subtype << p.string(")"))
    return Strain(
        flutype=flutype, host=host, place=place, year=year, ident=ident, subtype=subtype
    )


p_strain_obj = p_s5 ^ p_s4 ^ p_s3
