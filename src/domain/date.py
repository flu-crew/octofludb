import parsec as p
from src.util import padDigit, rmNone
from rdflib.namespace import XSD
from rdflib import Literal


def expandYear(x: str) -> str:
    """Expand years: [1-9]X -> 19XX and 0X -> 200X"""
    if len(x) == 2:
        if int(x[0]) <= 2:
            x = "20" + x  # 00-29 are cast as 2000-2019
        else:
            x = "19" + x  # 30-99 are cast as 1920-1999
    return x


class Date:
    def __init__(self, year: str, month: str = None, day: str = None):
        self.year = year
        self.month = month
        self.day = day

    def as_uri(self):
        # 2015
        if self.year and self.month is None:
            uri = Literal(self.year, datatype=XSD.gYear)
        # 2015/05
        elif self.year and self.month and self.day is None:
            uri = Literal(f"{self.year}-{self.month}", datatype=XSD.gYearMonth)
        # 2015/05/31
        elif self.year and self.month and self.day:
            uri = Literal(f"{self.year}-{self.month}-{self.day}", datatype=XSD.date)
        # 05/31
        elif self.year is None and self.month and self.day:
            uri = Literal(f"{self.month}-{self.day}", datatype=XSD.gMonthDay)
        # 05
        elif self.year is None and self.month and self.day is None:
            uri = Literal(f"{self.month}", datatype=XSD.gMonth)
        # 31
        elif self.year is None and self.month is None and self.day:
            uri = Literal(f"{self.day}", datatype=XSD.gDay)
        else:
            uri = None
        return uri

    def __str__(self):
        return "-".join(rmNone([self.year, self.month, self.day]))


@p.generate
def p_date_ymd():
    y = yield p_longyear
    yield p.optional(p.regex("[-/]"))
    m = yield p_month
    yield p.optional(p.regex("[-/]"))
    d = yield p_day
    return Date(month=m, day=d, year=y)


@p.generate
def p_date_mdy():
    m = yield p_month
    yield p.optional(p.regex("[-/]"))
    d = yield p_day
    yield p.optional(p.regex("[-/]"))
    y = yield p_longyear
    return Date(month=m, day=d, year=y)


@p.generate
def p_date_my():
    m = yield p_month
    yield p.regex("[-/]")
    y = yield p_longyear
    return Date(month=m, year=y)


@p.generate
def p_date_ym():
    y = yield p_longyear
    yield p.regex("[-/]")
    m = yield p_month
    return Date(month=m, year=y)


p_year = p.regex("20\d\d") ^ p.regex("19\d\d") ^ p.regex("\d\d").parsecmap(expandYear)
p_longyear = p.regex("20\d\d") | p.regex("19\d\d")
p_month = p.regex("10|11|12|0?[1-9]").parsecmap(padDigit)
p_day = p.regex("3[01]|[012]?\d").parsecmap(padDigit)

p_date = p_date_ymd ^ p_date_mdy

p_any_date = (
    p_date_ymd
    ^ p_date_mdy
    ^ p_date_my
    ^ p_date_ym
    ^ p_year.parsecmap(lambda y: Date(year=y))
)
