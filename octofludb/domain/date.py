import parsec as p
from octofludb.util import padDigit, rmNone
from octofludb.parser import wordset
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
    yield p.optional(p.regex(" \d\d:\d\d:\d\d(\.\d+)?"))
    return Date(month=m, day=d, year=y)


@p.generate
def p_date_mdy():
    m = yield p_month
    yield p.optional(p.regex("[-/]"))
    d = yield p_day
    yield p.optional(p.regex("[-/]"))
    y = yield p_longyear
    yield p.optional(p.regex(" \d\d:\d\d:\d\d(\.\d+)?"))
    return Date(month=m, day=d, year=y)


@p.generate
def p_date_dMy():
    """
    01-Apr-2002
    """
    d = yield p_day
    yield p.optional(p.regex("[-/]"))
    m = yield p_month_str
    yield p.optional(p.regex("[-/]"))
    y = yield p_year
    yield p.optional(p.regex(" \d\d:\d\d:\d\d(\.\d+)?"))
    return Date(month=m, day=d, year=y)


@p.generate
def p_date_polite():
    """
    May 31, 2018
    """
    m = yield p_month_str
    yield p.spaces()
    d = yield p_day
    yield p.string(",")
    yield p.spaces()
    y = yield p_longyear
    return Date(day=d, month=m, year=y)


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


@p.generate
def p_utc_date():
    y = yield p_longyear
    yield p.optional(p.string("-"))
    m = yield p_month_num
    yield p.optional(p.string("-"))
    d = yield p_day
    yield p.string("T")
    yield p_iso8601_time
    return Date(year=y, month=m, day=d)


@p.generate
def p_iso8601_time():
    h = yield p_hour
    yield p.optional(p.string(":"))
    m = yield p_minute
    yield p.optional(p.string(":"))
    s = yield p_second
    yield p.optional((p.string("Z") | (p.string("+") >> p.regex("\d\d:\d\d"))))
    return h + m + s


p_hour = p.regex("[01]\d") ^ p.regex("2[0-3]")
p_minute = p.regex("[0-5]\d")
p_second = p.regex("[0-5]\d")


p_year = p.regex("20\d\d") ^ p.regex("1\d\d\d") ^ p.regex("\d\d").parsecmap(expandYear)
p_longyear = p.regex("20\d\d") | p.regex("1[89]\d\d")
p_day = p.regex("3[01]|[012]?\d").parsecmap(padDigit)

months = {
    "jan": "1",
    "feb": "2",
    "mar": "3",
    "apr": "4",
    "may": "5",
    "jun": "6",
    "jul": "7",
    "aug": "8",
    "sep": "9",
    "oct": "10",
    "nov": "11",
    "dec": "12",
    "january": "1 ",
    "february": "2",
    "march": "3",
    "april": "4",
    "may": "5",
    "june": "6",
    "july": "7",
    "august": "8",
    "september": "9",
    "october": "10",
    "november": "11",
    "december": "12",
}

p_month_num = p.regex("10|11|12|0?[1-9]").parsecmap(padDigit)
p_month_str = (
    wordset(months.keys(), "date")
    .parsecmap(lambda x: months[x.lower()])
    .parsecmap(padDigit)
)
p_month = p_month_num ^ p_month_str

p_date = p_utc_date ^ p_date_polite ^ p_date_ymd ^ p_date_mdy ^ p_date_dMy

p_any_date = (
    p_utc_date
    ^ p_date_polite
    ^ p_date_dMy
    ^ p_date_ymd
    ^ p_date_mdy
    ^ p_date_my
    ^ p_date_ym
    ^ p_year.parsecmap(lambda y: Date(year=y))
)
