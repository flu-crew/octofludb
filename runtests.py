#!/usr/bin/env python3

import src.parser as parser
import src.domain.geography as geo
from src.nomenclature import make_uri, make_usa_state_uri, make_country_uri
import unittest
import urllib.parse as url


class TestParsers(unittest.TestCase):
    def test_p_country(self):
        self.assertEqual(parser.p_country.parse("USA"), "USA")
        self.assertEqual(parser.p_country.parse("indonesia"), "indonesia")

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
        x="!@#$%^&*()/:;'\",.<>yolo!"
        self.assertTrue(url.quote_plus(x) in make_uri(x))

    def test_make_state_uri(self):
        self.assertEqual(make_usa_state_uri("wyoming"), make_usa_state_uri("WY"))
        self.assertEqual(make_usa_state_uri("north dakota "), make_usa_state_uri("North Dakota"))

    def test_make_country_uri(self):
        self.assertEqual(make_country_uri("usa"), make_country_uri("united states of america"))
        self.assertEqual(make_country_uri("USA"), make_country_uri("united states of america"))
        self.assertEqual(make_country_uri("britain"), make_country_uri("UK"))


if __name__ == "__main__":
    unittest.main()
