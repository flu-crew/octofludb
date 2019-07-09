#!/usr/bin/env python3

import src.parser as parser
import src.domain.geography as geo
from src.nomenclature import make_uri, make_date, make_usa_state_uri, make_country_uri
import unittest
import urllib.parse as url
from rdflib.namespace import XSD
from rdflib import Literal


class TestNomenclature(unittest.TestCase):
    def test_make_date(self):
        # The make_date function is intended to be a catchall for when
        # something really really should be a date. It tries very hard to
        # match.
        # * Y
        self.assertEqual(make_date("2011"), Literal("2011", datatype=XSD.gYear))
        # 2-digit years are cast in 19XX is greater than 29
        self.assertEqual(make_date("99"), Literal("1999", datatype=XSD.gYear))
        self.assertEqual(make_date("00"), Literal("2000", datatype=XSD.gYear))
        self.assertEqual(make_date("29"), Literal("2029", datatype=XSD.gYear))
        self.assertEqual(make_date("30"), Literal("1930", datatype=XSD.gYear))
        # * YM
        self.assertEqual(
            make_date("2011/05"), Literal("2011/05", datatype=XSD.gYearMonth)
        )
        # * MY
        self.assertEqual(
            make_date("05/2011"), Literal("2011/05", datatype=XSD.gYearMonth)
        )
        # * YMD
        self.assertEqual(
            make_date("2011/05/31"), Literal("2011/05/31", datatype=XSD.date)
        )
        self.assertEqual(
            make_date("20110531"), Literal("2011/05/31", datatype=XSD.date)
        )
        # * MDY
        self.assertEqual(
            make_date("05/31/2011"), Literal("2011/05/31", datatype=XSD.date)
        )
        self.assertEqual(
            make_date("05312011"), Literal("2011/05/31", datatype=XSD.date)
        )
        # * DO NOT SUPPORT SHORT YEARS
        self.assertEqual(make_date("11/05"), None)
        self.assertEqual(make_date("05/11"), None)
        self.assertEqual(make_date("11/05/31"), None)
        self.assertEqual(make_date("05/31/11"), None)
        # make_date must match the entire input string, so these should fail:
        self.assertEqual(make_date("20195"), None)
        self.assertEqual(make_date("201905067"), None)
        self.assertEqual(make_date("05/06/01/6"), None)
        self.assertEqual(make_date("asdf"), None)
        # TODO: allow month names to be parsed (e.g. "May 5, 2019")


class TestParsers(unittest.TestCase):
    def test_p_country(self):
        self.assertEqual(parser.p_country.parse("USA"), "USA")
        self.assertEqual(parser.p_country.parse("indonesia"), "indonesia")

    def test_p_date(self):
        self.assertEqual(str(parser.p_date.parse("2015/09/01")), "2015-09-01")
        self.assertEqual(
            str(parser.p_date.parse("09/01/2015")),
            str(parser.p_date.parse("2015/09/01")),
        )
        self.assertEqual(
            str(parser.p_date.parse("09-01-2015")),
            str(parser.p_date.parse("2015/09/01")),
        )

    def test_p_year(self):
        self.assertEqual(parser.p_year.parse("09"), parser.p_year.parse("2009"))

    def test_country_to_code(self):
        self.assertEqual(geo.country_to_code("united states"), "USA")
        self.assertEqual(geo.country_to_code("US"), "USA")
        self.assertEqual(geo.country_to_code("USA"), "USA")
        self.assertEqual(
            geo.country_to_code("The Democratic Republic of the Congo"), "COD"
        )
        self.assertEqual(geo.country_to_code("democratic republic of the congo"), "COD")

    def test_state_to_code(self):
        self.assertEqual(geo.state_to_code("wyoming"), ("WY"))
        self.assertEqual(geo.state_to_code("WY"), ("WY"))
        self.assertEqual(geo.state_to_code("Wyoming"), ("WY"))
        self.assertEqual(geo.state_to_code("District of Columbia"), ("DC"))
        self.assertEqual(geo.state_to_code("North_Dakota"), ("ND"))
        self.assertEqual(geo.state_to_code("North dakota"), ("ND"))

    def test_make_uri(self):
        # space/underscore differences shouldn't yield different URIs
        self.assertEqual(make_uri("foo bar baz"), make_uri("foo_bar_baz"))
        self.assertEqual(make_uri("foo bar_baz"), make_uri("foo bar_baz"))
        # capitalization shouldn't matter
        self.assertEqual(make_uri("Foo bAr Baz"), make_uri("fOo_baR_baZ"))
        # trailing space shouldn't matter
        self.assertEqual(make_uri(" Foo bAr Baz   "), make_uri("fOo_baR_baZ"))
        # multiple spaces should be the same as a single space
        self.assertEqual(make_uri(" Foo   bAr Baz   "), make_uri("fOo_baR_baZ"))
        # special variables should be quoted
        x = "!@#$%^&*()/:;'\",.<>yolo!"
        self.assertTrue(url.quote_plus(x) in make_uri(x))

    def test_make_state_uri(self):
        self.assertEqual(make_usa_state_uri("wyoming"), make_usa_state_uri("WY"))
        self.assertEqual(
            make_usa_state_uri("north dakota "), make_usa_state_uri("North Dakota")
        )

    def test_make_country_uri(self):
        self.assertEqual(
            make_country_uri("usa"), make_country_uri("united states of america")
        )
        self.assertEqual(
            make_country_uri("USA"), make_country_uri("united states of america")
        )
        self.assertEqual(make_country_uri("britain"), make_country_uri("UK"))


if __name__ == "__main__":
    unittest.main()
