#!/usr/bin/env python3

import src.classifiers.flucrew as ftok
from src.nomenclature import make_uri, make_usa_state_uri, make_country_uri
import unittest
import rdflib
import urllib.parse as url


class TestMakeUri(unittest.TestCase):
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


class TestDate(unittest.TestCase):
    def test_date_meta(self):
        d = ftok.Date("May 17, 1986")
        self.assertEqual(d.clean, "1986-05-17")
        self.assertEqual(d.dirty, "May 17, 1986")
        self.assertEqual(d.as_uri(), None)  # dates should NEVER be URIs
        self.assertEqual(
            d.as_literal(), rdflib.Literal("1986-05-17", datatype=rdflib.XSD.date)
        )
        y = ftok.Date("1990")
        self.assertEqual(
            y.as_literal(), rdflib.Literal("1990", datatype=rdflib.XSD.gYear)
        )

    def test_year(self):
        self.assertEqual(ftok.Date("2011").clean, "2011")
        self.assertEqual(ftok.Date("11").clean, "2011")
        self.assertEqual(ftok.Date("90").clean, "1990")
        # 2-digit years are cast in 19XX is greater than 29
        self.assertEqual(
            ftok.Date("99").as_literal(),
            rdflib.Literal("1999", datatype=rdflib.XSD.gYear),
        )
        self.assertEqual(
            ftok.Date("00").as_literal(),
            rdflib.Literal("2000", datatype=rdflib.XSD.gYear),
        )
        self.assertEqual(
            ftok.Date("29").as_literal(),
            rdflib.Literal("2029", datatype=rdflib.XSD.gYear),
        )
        self.assertEqual(
            ftok.Date("30").as_literal(),
            rdflib.Literal("1930", datatype=rdflib.XSD.gYear),
        )

    def test_ymd(self):
        self.assertEqual(ftok.Date("05-Jun-2011").clean, "2011-06-05")
        self.assertEqual(ftok.Date("Jun-2011").clean, "2011-06")
        self.assertEqual(ftok.Date("May 17, 1986").clean, "1986-05-17")
        self.assertEqual(ftok.Date("May17,1986").clean, "1986-05-17")
        self.assertEqual(ftok.Date("1986-05-17").clean, "1986-05-17")
        self.assertEqual(ftok.Date("19860517").clean, "1986-05-17")
        self.assertEqual(ftok.Date("1986/05/17").clean, "1986-05-17")
        self.assertEqual(ftok.Date("05/17/1986").clean, "1986-05-17")
        self.assertEqual(ftok.Date("1986-05-17").clean, "1986-05-17")
        # testing year ranges
        self.assertEqual(ftok.Date("05/17/1886").clean, "1886-05-17")

    def test_partial_dates(self):
        # * YM
        self.assertEqual(
            ftok.Date("2011/05").as_literal(),
            rdflib.Literal("2011-05", datatype=rdflib.XSD.gYearMonth),
        )
        # * MY
        self.assertEqual(
            ftok.Date("05/2011").as_literal(),
            rdflib.Literal("2011-05", datatype=rdflib.XSD.gYearMonth),
        )
        # * YMD
        self.assertEqual(
            ftok.Date("2011/05/31").as_literal(),
            rdflib.Literal("2011-05-31", datatype=rdflib.XSD.date),
        )
        self.assertEqual(
            ftok.Date("20110531").as_literal(),
            rdflib.Literal("2011-05-31", datatype=rdflib.XSD.date),
        )
        # * MDY
        self.assertEqual(
            ftok.Date("05/31/2011").as_literal(),
            rdflib.Literal("2011-05-31", datatype=rdflib.XSD.date),
        )
        self.assertEqual(
            ftok.Date("05312011").as_literal(),
            rdflib.Literal("2011-05-31", datatype=rdflib.XSD.date),
        )

    def test_utc(self):
        self.assertEqual(ftok.Date("1986-05-17T22:01:30Z").clean, "1986-05-17")
        self.assertEqual(ftok.Date("1986-05-17T22:01:30+00:00").clean, "1986-05-17")

    def test_bad_dates(self):
        # Dates that I won't accept (there clemency has limits)
        self.assertEqual(ftok.Date("May 17, 19").clean, None)
        self.assertEqual(ftok.Date("05 17, 1999").clean, None)
        self.assertEqual(ftok.Date("05/17/86").clean, None)
        # * DO NOT SUPPORT SHORT YEARS
        self.assertEqual(ftok.Date("11/05").clean, None)
        self.assertEqual(ftok.Date("05/11").clean, None)
        self.assertEqual(ftok.Date("11/05/31").clean, None)
        self.assertEqual(ftok.Date("05/31/11").clean, None)
        # ftok.Date must match the entire input string, so these should fail:
        self.assertEqual(ftok.Date("20195").clean, None)
        self.assertEqual(ftok.Date("201905067").clean, None)
        self.assertEqual(ftok.Date("05/06/01/6").clean, None)
        self.assertEqual(ftok.Date("asdf").clean, None)


class TestCountry(unittest.TestCase):
    def test_country(self):
        self.assertEqual(ftok.Country("USA").clean, "USA")
        self.assertEqual(ftok.Country("united states").clean, "USA")
        self.assertEqual(ftok.Country("US").clean, "USA")
        self.assertEqual(ftok.Country("indonesia").clean, "IDN")
        self.assertEqual(
            ftok.Country("The Democratic Republic of the Congo").clean, "COD"
        )
        self.assertEqual(ftok.Country("democratic republic congo").clean, "COD")

    def test_misspelled_countries(self):
        self.assertEqual(ftok.Country("unitde states").clean, "USA")
        self.assertEqual(ftok.Country("indoesia").clean, "IDN")
        self.assertEqual(ftok.Country("indonesa").clean, "IDN")


class TestState(unittest.TestCase):
    def test_state_to_code(self):
        self.assertEqual(ftok.StateUSA("wyoming").clean, ("WY"))
        self.assertEqual(ftok.StateUSA("WY").clean, ("WY"))
        self.assertEqual(ftok.StateUSA("District of Columbia").clean, ("DC"))
        self.assertEqual(ftok.StateUSA("North_Dakota").clean, ("ND"))
        self.assertEqual(ftok.StateUSA("North dakota").clean, ("ND"))


if __name__ == "__main__":
    unittest.main()
