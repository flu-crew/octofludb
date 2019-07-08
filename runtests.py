#!/usr/bin/env python3

import src.parser as parser
import src.domain.geography as geo
import unittest


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


if __name__ == "__main__":
    unittest.main()
