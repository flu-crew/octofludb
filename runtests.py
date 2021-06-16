#!/usr/bin/env python3

import octofludb.classifiers.flucrew as ftok
import octofludb.recipes as recipes
import octofludb.formatting as formatter
import octofludb.token as tok
from octofludb.nomenclature import (
    make_uri,
    make_usa_state_uri,
    make_country_uri,
    make_property,
)
from octofludb.classes import HomoList, Phrase, Datum, Ragged
from octofludb.graph import showTriple
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

    def test_make_property(self):
        self.assertEqual(make_property("foo baR Baz"), make_property("Foo_bar Baz"))

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


class TestInteger(unittest.TestCase):
    def test_Integer(self):
        self.assertEqual(tok.Integer("1").clean, "1")
        self.assertEqual(tok.Integer("0").clean, "0")
        self.assertEqual(tok.Integer("12345678").clean, "12345678")
        self.assertEqual(tok.Integer("12345678.0").clean, None)
        self.assertEqual(tok.Integer("bogus").clean, None)


class TestDouble(unittest.TestCase):
    def test_Double(self):
        self.assertEqual(tok.Double("1").clean, "1")
        self.assertEqual(tok.Double("0").clean, "0")
        self.assertEqual(tok.Double("12345678").clean, "12345678")
        self.assertEqual(tok.Double("12345678.0").clean, "12345678.0")
        self.assertEqual(tok.Double("bogus").clean, None)


class TestBoolean(unittest.TestCase):
    def test_Boolean(self):
        self.assertEqual(tok.Boolean("1").clean, "true")
        self.assertEqual(tok.Boolean("y").clean, "true")
        self.assertEqual(tok.Boolean("t").clean, "true")
        self.assertEqual(tok.Boolean("yeS").clean, "true")
        self.assertEqual(tok.Boolean("tRuE").clean, "true")
        self.assertEqual(tok.Boolean("0").clean, "false")
        self.assertEqual(tok.Boolean("n").clean, "false")
        self.assertEqual(tok.Boolean("nO").clean, "false")
        self.assertEqual(tok.Boolean("faLse").clean, "false")
        self.assertEqual(tok.Boolean("bogus").clean, None)


class TestBarcode(unittest.TestCase):
    def test_Barcode(self):
        self.assertEqual(ftok.Barcode("A01234567").clean, "A01234567")
        self.assertEqual(ftok.Barcode("bogus").clean, None)
        self.assertEqual(ftok.Barcode("K00869").clean, None)


class TestConstellation(unittest.TestCase):
    def test_Constellation(self):
        self.assertEqual(ftok.Constellation("TTPVVP").clean, "TTPVVP")
        self.assertEqual(ftok.Constellation("T-----").clean, "T-----")
        self.assertEqual(ftok.Constellation("XXXXXX").clean, "XXXXXX")
        self.assertEqual(ftok.Constellation("MIXED").clean, "MIXED")
        self.assertEqual(ftok.Constellation("bogus").clean, None)


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

    def test_bad_countries(self):
        self.assertEqual(ftok.Country("bogus").clean, None)


class TestCountryOrState(unittest.TestCase):
    def test_country(self):
        self.assertEqual(ftok.CountryOrState("USA").clean, "USA")
        self.assertEqual(ftok.CountryOrState("united states").clean, "USA")
        self.assertEqual(ftok.CountryOrState("US").clean, "USA")
        self.assertEqual(ftok.CountryOrState("indonesia").clean, "IDN")
        self.assertEqual(
            ftok.CountryOrState("The Democratic Republic of the Congo").clean, "COD"
        )
        self.assertEqual(ftok.CountryOrState("democratic republic congo").clean, "COD")

    def test_misspelled_countries(self):
        self.assertEqual(ftok.CountryOrState("unitde states").clean, "USA")
        self.assertEqual(ftok.CountryOrState("indoesia").clean, "IDN")
        self.assertEqual(ftok.CountryOrState("indonesa").clean, "IDN")

    def test_bad_countries(self):
        self.assertEqual(ftok.CountryOrState("bogus").clean, None)

    def test_canada(self):
        self.assertEqual(
            ftok.CountryOrState("quebec").clean, ftok.Country("canada").clean
        )
        self.assertEqual(
            ftok.CountryOrState("ontario").clean, ftok.Country("canada").clean
        )

    def test_chinese_provinces(self):
        self.assertEqual(
            ftok.CountryOrState("jiangsu").clean, ftok.Country("china").clean
        )

    def test_usa_states(self):
        self.assertEqual(
            ftok.CountryOrState("alabama").clean, ftok.Country("usa").clean
        )


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
        self.assertEqual(ftok.Date("bogus").clean, None)


class TestGenbank(unittest.TestCase):
    def test_Genbank(self):
        self.assertEqual(ftok.Genbank("AB12345678").clean, None)
        self.assertEqual(ftok.Genbank("AB1234567").clean, "AB1234567")
        self.assertEqual(ftok.Genbank("AB123456").clean, "AB123456")
        self.assertEqual(ftok.Genbank("AB12345").clean, "AB12345")
        self.assertEqual(ftok.Genbank("AB1234").clean, None)
        self.assertEqual(ftok.Genbank("ABC1234").clean, None)
        # there can be just 1 letter
        self.assertEqual(ftok.Genbank("A1234567").clean, "A1234567")
        self.assertEqual(ftok.Genbank("A123456").clean, "A123456")
        self.assertEqual(ftok.Genbank("A12345").clean, "A12345")
        self.assertEqual(ftok.Genbank("K00869").clean, "K00869")
        # capitalization is required for now
        self.assertEqual(ftok.Genbank("a12345").clean, None)
        self.assertEqual(ftok.Genbank("ab12345").clean, None)
        self.assertEqual(ftok.Genbank("bogus").clean, None)


class TestEpiSeqid(unittest.TestCase):
    def test_EpiSeqid(self):
        # no upper bound on integers
        self.assertEqual(ftok.EpiSeqid("EPI_1234567890123").clean, "EPI1234567890123")
        # underscore optional
        self.assertEqual(ftok.EpiSeqid("EPI1234567890123").clean, "EPI1234567890123")
        # but at least 3
        self.assertEqual(ftok.EpiSeqid("EPI_123").clean, "EPI123")
        # currently I don't allow fewer than 2 numbers
        self.assertEqual(ftok.EpiSeqid("EPI_12").clean, None)
        self.assertEqual(ftok.EpiSeqid("bogus").clean, None)


class TestGlobalClade(unittest.TestCase):
    def test_GlobalClade(self):
        self.assertEqual(ftok.GlobalClade("1A.1").clean, "1A.1")
        # or underscores or dashes
        self.assertEqual(ftok.GlobalClade("1A_1_34").clean, "1A_1_34")
        self.assertEqual(ftok.GlobalClade("1A_1-34").clean, "1A_1-34")
        # may have like
        self.assertEqual(ftok.GlobalClade("1A_1_34_like").clean, "1A_1_34_like")
        self.assertEqual(ftok.GlobalClade("1A_1_34like").clean, "1A_1_34like")
        self.assertEqual(ftok.GlobalClade("1A_1_34-like").clean, "1A_1_34-like")
        # up to four expressions
        self.assertEqual(ftok.GlobalClade("1A.1.2.34.234").clean, "1A.1.2.34.234")
        # but not 5
        self.assertEqual(ftok.GlobalClade("1A.1.2.34.234.3").clean, None)
        # current octoflu strain names
        self.assertEqual(ftok.GlobalClade("1A.1").clean, "1A.1")
        self.assertEqual(ftok.GlobalClade("1A.1.1").clean, "1A.1.1")
        self.assertEqual(ftok.GlobalClade("1A.2").clean, "1A.2")
        self.assertEqual(ftok.GlobalClade("1A.2-3-like").clean, "1A.2-3-like")
        self.assertEqual(ftok.GlobalClade("1A.3.1").clean, "1A.3.1")
        self.assertEqual(ftok.GlobalClade("1A.3.3.2").clean, "1A.3.3.2")
        self.assertEqual(ftok.GlobalClade("1A.3.3.2-vaccine").clean, "1A.3.3.2-vaccine")
        self.assertEqual(ftok.GlobalClade("1A.3.3.3").clean, "1A.3.3.3")
        self.assertEqual(ftok.GlobalClade("1B.2.1").clean, "1B.2.1")
        self.assertEqual(ftok.GlobalClade("1B.2.2").clean, "1B.2.2")
        self.assertEqual(ftok.GlobalClade("1B.2.2.1").clean, "1B.2.2.1")
        self.assertEqual(ftok.GlobalClade("1B.2.2.2").clean, "1B.2.2.2")
        self.assertEqual(ftok.GlobalClade("1C.2").clean, "1C.2")
        self.assertEqual(ftok.GlobalClade("3.1970.1").clean, "3.1970.1")
        self.assertEqual(ftok.GlobalClade("3.1980.1").clean, "3.1980.1")
        self.assertEqual(ftok.GlobalClade("3.1990.1").clean, "3.1990.1")
        self.assertEqual(ftok.GlobalClade("3.1990.2").clean, "3.1990.2")
        self.assertEqual(ftok.GlobalClade("3.1990.4").clean, "3.1990.4")
        self.assertEqual(ftok.GlobalClade("3.1990.4.1").clean, "3.1990.4.1")
        self.assertEqual(ftok.GlobalClade("3.1990.4.2-3").clean, "3.1990.4.2-3")
        self.assertEqual(ftok.GlobalClade("3.1990.4.4").clean, "3.1990.4.4")
        self.assertEqual(ftok.GlobalClade("3.1990.4.6").clean, "3.1990.4.6")
        self.assertEqual(ftok.GlobalClade("3.1990.4.a").clean, "3.1990.4.a")
        self.assertEqual(ftok.GlobalClade("3.1990.4.b1").clean, "3.1990.4.b1")
        self.assertEqual(ftok.GlobalClade("3.2010.1").clean, "3.2010.1")
        self.assertEqual(ftok.GlobalClade("3.2010.2").clean, "3.2010.2")
        self.assertEqual(ftok.GlobalClade("3.2010.4").clean, "3.2010.4")
        self.assertEqual(ftok.GlobalClade("Other-Avian").clean, "Other-Avian")
        self.assertEqual(ftok.GlobalClade("Other-Avian-c2").clean, "Other-Avian-c2")
        self.assertEqual(ftok.GlobalClade("Other-Avian-c4").clean, "Other-Avian-c4")
        self.assertEqual(ftok.GlobalClade("Other-Equine").clean, "Other-Equine")
        self.assertEqual(ftok.GlobalClade("Other-Human-1960").clean, "Other-Human-1960")
        self.assertEqual(ftok.GlobalClade("Other-Human-1970").clean, "Other-Human-1970")
        self.assertEqual(ftok.GlobalClade("Other-Human-1980").clean, "Other-Human-1980")
        self.assertEqual(ftok.GlobalClade("Other-Human-1990").clean, "Other-Human-1990")
        self.assertEqual(ftok.GlobalClade("Other-Human-1B.2").clean, "Other-Human-1B.2")
        self.assertEqual(ftok.GlobalClade("Other-Human-2000").clean, "Other-Human-2000")
        self.assertEqual(ftok.GlobalClade("Outgroup").clean, "Outgroup")
        self.assertEqual(ftok.GlobalClade("humanVaccine").clean, "humanVaccine")
        # test bad data
        self.assertEqual(ftok.GlobalClade("bogus").clean, None)


class TestSubtype(unittest.TestCase):
    def test_Subtype(self):
        self.assertEqual(ftok.Subtype("H1N1").clean, "H1N1")
        # or any number ...
        self.assertEqual(ftok.Subtype("H11N12").clean, "H11N12")
        # with possible variants
        self.assertEqual(ftok.Subtype("H1N1v").clean, "H1N1v")
        # with possible species annotations with and without v
        self.assertEqual(ftok.Subtype("H1huN1v").clean, "H1huN1v")
        self.assertEqual(ftok.Subtype("H1swN1v").clean, "H1swN1v")
        self.assertEqual(ftok.Subtype("H1avN1v").clean, "H1avN1v")
        self.assertEqual(ftok.Subtype("H1huN1").clean, "H1huN1")
        self.assertEqual(ftok.Subtype("H1swN1").clean, "H1swN1")
        self.assertEqual(ftok.Subtype("H1avN1").clean, "H1avN1")
        # only hu, sw, and av species are supported for now
        self.assertEqual(ftok.Subtype("H1laN1").clean, None)
        # no lower
        self.assertEqual(ftok.Subtype("h1n1").clean, None)
        # allow type
        self.assertEqual(ftok.Subtype("A / H1N1").clean, "H1N1")
        self.assertEqual(ftok.Subtype("A/H1N1").clean, "H1N1")
        # subtypes may be mixed, which should be case-insensitive
        self.assertEqual(ftok.Subtype("Mixed").clean, "mixed")
        self.assertEqual(ftok.Subtype("mixed").clean, "mixed")
        self.assertEqual(ftok.Subtype("MiXeD").clean, "mixed")
        # die correctly on bad input
        self.assertEqual(ftok.Subtype("bogus").clean, None)


class TestHA(unittest.TestCase):
    def test_HA(self):
        self.assertEqual(ftok.HA("H1").clean, "H1")
        self.assertEqual(ftok.HA("H10").clean, "H10")
        self.assertEqual(ftok.HA("pdmH1").clean, "pdmH1")
        # no lower
        self.assertEqual(ftok.HA("h1").clean, None)
        self.assertEqual(ftok.HA("bogus").clean, None)


class TestNA(unittest.TestCase):
    def test_NA(self):
        self.assertEqual(ftok.NA("N1").clean, "N1")
        self.assertEqual(ftok.NA("N10").clean, "N10")
        # no lower
        self.assertEqual(ftok.NA("n10").clean, None)
        self.assertEqual(ftok.NA("bogus").clean, None)


class TestHost(unittest.TestCase):
    def test_Host(self):
        # munged to lowercase
        self.assertEqual(ftok.Host("Swine").clean, "swine")
        self.assertEqual(ftok.Host("Human").clean, "human")
        self.assertEqual(ftok.Host("HuMaN").clean, "human")
        # FIXME: currently no other hosts are supported, but this needs to change
        self.assertEqual(ftok.Host("chicken").clean, None)
        self.assertEqual(ftok.Host("bogus").clean, None)


class TestInternalGene(unittest.TestCase):
    def test_InternalGene(self):
        self.assertEqual(ftok.InternalGene("PB2").clean, "PB2")
        self.assertEqual(ftok.InternalGene("PB1").clean, "PB1")
        self.assertEqual(ftok.InternalGene("PA").clean, "PA")
        self.assertEqual(ftok.InternalGene("NP").clean, "NP")
        self.assertEqual(ftok.InternalGene("M").clean, "M")
        self.assertEqual(ftok.InternalGene("MP").clean, "M")
        # The M1 is required for parsing genbanks, which store the segment name
        # under the key "gene" as M1. This is the name of the protein subunit.
        self.assertEqual(ftok.InternalGene("M1").clean, "M")
        self.assertEqual(ftok.InternalGene("NS1").clean, "NS")
        self.assertEqual(ftok.InternalGene("NS").clean, "NS")
        # but not HA and NA
        self.assertEqual(ftok.InternalGene("H1").clean, None)
        self.assertEqual(ftok.InternalGene("HA").clean, None)
        self.assertEqual(ftok.InternalGene("NA").clean, None)
        self.assertEqual(ftok.InternalGene("N1").clean, None)
        self.assertEqual(ftok.InternalGene("bogus").clean, None)


class TestSegmentName(unittest.TestCase):
    def test_SegmentName(self):
        self.assertEqual(ftok.SegmentName("PB2").clean, "PB2")
        self.assertEqual(ftok.SegmentName("PB1").clean, "PB1")
        self.assertEqual(ftok.SegmentName("PA").clean, "PA")
        self.assertEqual(ftok.SegmentName("NP").clean, "NP")
        self.assertEqual(ftok.SegmentName("M").clean, "M")
        self.assertEqual(ftok.SegmentName("NS1").clean, "NS")
        self.assertEqual(ftok.SegmentName("HA").clean, "HA")
        self.assertEqual(ftok.SegmentName("NA").clean, "NA")
        self.assertEqual(ftok.SegmentName("bogus").clean, None)
        self.assertEqual(ftok.SegmentName("H1").clean, None)
        self.assertEqual(ftok.SegmentName("N1").clean, None)

    def test_AlternativeSegmentNames(self):
        self.assertEqual(ftok.SegmentName("MP").clean, "M")


class TestSegmentSubtype(unittest.TestCase):
    def test_SegmentSubtype(self):
        self.assertEqual(ftok.SegmentSubtype("PB2").clean, "PB2")
        self.assertEqual(ftok.SegmentSubtype("PB1").clean, "PB1")
        self.assertEqual(ftok.SegmentSubtype("PA").clean, "PA")
        self.assertEqual(ftok.SegmentSubtype("NP").clean, "NP")
        self.assertEqual(ftok.SegmentSubtype("M").clean, "M")
        self.assertEqual(ftok.SegmentSubtype("NS1").clean, "NS")
        self.assertEqual(ftok.SegmentSubtype("H1").clean, "H1")
        self.assertEqual(ftok.SegmentSubtype("H3").clean, "H3")
        self.assertEqual(ftok.SegmentSubtype("HA").clean, "HA")
        self.assertEqual(ftok.SegmentSubtype("NA").clean, "NA")
        self.assertEqual(ftok.SegmentSubtype("N1").clean, "N1")
        self.assertEqual(ftok.SegmentSubtype("N2").clean, "N2")
        self.assertEqual(ftok.SegmentSubtype("bogus").clean, None)


class TestSegmentNumber(unittest.TestCase):
    def test_SegmentNumber(self):
        self.assertEqual(ftok.SegmentNumber("0").clean, None)
        self.assertEqual(ftok.SegmentNumber("1").clean, "1")
        self.assertEqual(ftok.SegmentNumber("8").clean, "8")
        self.assertEqual(ftok.SegmentNumber("9").clean, None)
        self.assertEqual(ftok.SegmentNumber("PB1").clean, None)
        self.assertEqual(ftok.SegmentNumber("H1").clean, None)
        self.assertEqual(ftok.SegmentNumber("HA").clean, None)
        self.assertEqual(ftok.SegmentNumber("bogus").clean, None)


class TestStrain(unittest.TestCase):
    def test_Strain(self):
        self.assertEqual(ftok.Strain("A/asdf/er").clean, "A/asdf/er")
        self.assertEqual(ftok.Strain("A/asdf/er  	").clean, "A/asdf/er")
        # support influenza A-D but not E (since there isn't one yet, and even
        # if there were, being pig people, we wouldn't care about it)
        self.assertEqual(ftok.Strain("A/asdf/2020").clean, "A/asdf/2020")
        self.assertEqual(ftok.Strain("B/asdf/2020").clean, "B/asdf/2020")
        self.assertEqual(ftok.Strain("C/asdf/2020").clean, "C/asdf/2020")
        self.assertEqual(ftok.Strain("D/asdf/2020").clean, "D/asdf/2020")
        # there is no E type
        self.assertEqual(ftok.Strain("E/asdf/2020").clean, None)
        # allow space, but munge it to underscores
        self.assertEqual(
            ftok.Strain("A/asdf foo bar/2020").clean, "A/asdf_foo_bar/2020"
        )
        # match removes parentheses
        self.assertEqual(ftok.Strain("A/asdf/2020()").clean, "A/asdf/2020")
        self.assertEqual(ftok.Strain("A/asdf/2020 ()").clean, "A/asdf/2020")
        self.assertEqual(ftok.Strain("A/asdf/2020[]").clean, "A/asdf/2020")
        self.assertEqual(ftok.Strain("A/asdf/2020 []").clean, "A/asdf/2020")
        self.assertEqual(ftok.Strain("A/asdf/2020(H1N1)").clean, "A/asdf/2020")
        self.assertEqual(ftok.Strain("A/asdf/2020 (H1N1)").clean, "A/asdf/2020")
        self.assertEqual(ftok.Strain("A/asdf/2020[H1N1]").clean, "A/asdf/2020")
        self.assertEqual(ftok.Strain("A/asdf/2020 [H1N1]").clean, "A/asdf/2020")
        # remove enclosing parentheses (there are lots of these in genbank)
        self.assertEqual(
            ftok.Strain("(A/Bratislava/6/97 (H3N2))").clean, "A/Bratislava/6/97"
        )
        # require at least two slashes
        self.assertEqual(ftok.Strain("A/bogus").clean, None)
        # otherwise return nothing
        self.assertEqual(ftok.Strain("bogus").clean, None)

    def test_strain_barcode_parsing(self):
        g = set()
        ftok.Strain("A/asdf/A01234567/sdf").add_triples(g)
        expected = sorted([(str(x), str(y), str(z)) for x, y, z in g])
        self.assertEqual(
            expected,
            [
                (
                    "https://flu-crew.org/id/a%2Fasdf%2Fa01234567%2Fsdf",
                    "https://flu-crew.org/term/barcode",
                    "A01234567",
                ),
                (
                    "https://flu-crew.org/id/a%2Fasdf%2Fa01234567%2Fsdf",
                    "https://flu-crew.org/term/strain_name",
                    "A/asdf/A01234567/sdf",
                ),
            ],
        )


class TestState(unittest.TestCase):
    def test_state_to_code(self):
        self.assertEqual(ftok.StateUSA("wyoming").clean, "WY")
        self.assertEqual(ftok.StateUSA("WY").clean, "WY")
        self.assertEqual(ftok.StateUSA("District of Columbia").clean, "DC")
        self.assertEqual(ftok.StateUSA("North_Dakota").clean, "ND")
        self.assertEqual(ftok.StateUSA("North dakota").clean, "ND")
        self.assertEqual(ftok.StateUSA("bogus").clean, None)


class TestInternalGeneClade(unittest.TestCase):
    def test_InternalGeneClade(self):
        self.assertEqual(ftok.InternalGeneClade("TRIG").clean, "TRIG")
        self.assertEqual(ftok.InternalGeneClade("PDM").clean, "PDM")
        self.assertEqual(ftok.InternalGeneClade("LAIV").clean, "LAIV")
        # convert to uppercase for internals
        self.assertEqual(ftok.InternalGeneClade("trig").clean, "TRIG")
        self.assertEqual(ftok.InternalGeneClade("pdm").clean, "PDM")
        self.assertEqual(ftok.InternalGeneClade("LaIv").clean, "LAIV")
        # don't accept random strings
        self.assertEqual(ftok.InternalGeneClade("bogus").clean, None)


class TestH1Clade(unittest.TestCase):
    def test_H1Clade(self):
        self.assertEqual(ftok.H1Clade("alpha").clean, "alpha")
        # do no alter case
        self.assertEqual(ftok.H1Clade("aLPHa").clean, "aLPHa")
        self.assertEqual(ftok.H1Clade("bogus").clean, None)


class TestH3Clade(unittest.TestCase):
    def test_H3Clade(self):
        self.assertEqual(ftok.H3Clade("2010.1").clean, "2010.1")
        self.assertEqual(ftok.H3Clade("bogus").clean, None)


class TestN1Clade(unittest.TestCase):
    def test_N1Clade(self):
        self.assertEqual(ftok.N1Clade("Classical").clean, "Classical")
        self.assertEqual(ftok.N1Clade("bogus").clean, None)


class TestN2Clade(unittest.TestCase):
    def test_N2Clade(self):
        self.assertEqual(ftok.N2Clade("1998A").clean, "1998A")


class TestDnaseq(unittest.TestCase):
    def test_Dnaseq(self):
        self.assertEqual(ftok.Dnaseq("A").clean, "A")
        self.assertEqual(
            ftok.Dnaseq("ATAGAGAGGGGTCCGCGCT").clean, "ATAGAGAGGGGTCCGCGCT"
        )
        self.assertEqual(ftok.Dnaseq("A_TR_YATTNN").clean, "ATRYATTNN")


class TestProseq(unittest.TestCase):
    def test_Proseq(self):
        # is valid protein sequence too
        self.assertEqual(ftok.Proseq("ATGAGAGA").clean, "ATGAGAGA")
        self.assertEqual(ftok.Proseq("GANDALF").clean, "GANDALF")
        self.assertEqual(ftok.Proseq("_PIC*K*L*E*").clean, "PIC*K*L*E*")


class TestUnknown(unittest.TestCase):
    def test_Unknown(self):
        # matches anything
        self.assertEqual(ftok.Unknown("").clean, "")
        self.assertEqual(ftok.Unknown("1").clean, "1")
        self.assertEqual(ftok.Unknown("a").clean, "a")
        self.assertEqual(ftok.Unknown("yOlO123").clean, "yOlO123")


class TestHomoList(unittest.TestCase):
    def types(self, xs):
        return [x.typename for x in HomoList(xs).data]

    def test_homolist(self):
        self.assertEqual(self.types(["Georgia"]), ["country"])
        self.assertEqual(self.types(["Georgia", "Texas"]), ["state", "state"])


class TestPhrase(unittest.TestCase):
    def test_phrase(self):
        self.assertEqual(
            showTriple(["A01234567", "H1N1"]),
            [
                (
                    "https://flu-crew.org/id/a01234567",
                    "https://flu-crew.org/term/barcode",
                    "A01234567",
                ),
                (
                    "https://flu-crew.org/id/a01234567",
                    "https://flu-crew.org/term/subtype",
                    "H1N1",
                ),
            ],
        )


class TestFasta(unittest.TestCase):
    def test_fasta(self):
        g = set()
        x = Ragged(">baz\nATGG\n>foo||z\nATGGG", na_str=[None])
        x.connect(g)
        s = sorted([(str(s), str(p), str(o)) for s, p, o in g])
        self.assertEqual(
            s,
            [
                (
                    "https://flu-crew.org/id/4badd1687f27faae29f9b1fe1ea37e78",
                    "https://flu-crew.org/term/chksum",
                    "4badd1687f27faae29f9b1fe1ea37e78",
                ),
                (
                    "https://flu-crew.org/id/4badd1687f27faae29f9b1fe1ea37e78",
                    "https://flu-crew.org/term/dnaseq",
                    "ATGGG",
                ),
                (
                    "https://flu-crew.org/id/4badd1687f27faae29f9b1fe1ea37e78",
                    "https://flu-crew.org/term/unknown",
                    "foo",
                ),
                (
                    "https://flu-crew.org/id/4badd1687f27faae29f9b1fe1ea37e78",
                    "https://flu-crew.org/term/unknown",
                    "z",
                ),
                (
                    "https://flu-crew.org/id/5b2033ab635505389b1acfa0d6eda05c",
                    "https://flu-crew.org/term/chksum",
                    "5b2033ab635505389b1acfa0d6eda05c",
                ),
                (
                    "https://flu-crew.org/id/5b2033ab635505389b1acfa0d6eda05c",
                    "https://flu-crew.org/term/dnaseq",
                    "ATGG",
                ),
                (
                    "https://flu-crew.org/id/5b2033ab635505389b1acfa0d6eda05c",
                    "https://flu-crew.org/term/unknown",
                    "baz",
                ),
            ],
        )

    def test_fasta_carriage(self):
        g1 = set()
        x1 = Ragged(">baz\nATGG\n>foo||z\nATGGG", na_str=[None])
        x1.connect(g1)
        s1 = sorted([(str(s), str(p), str(o)) for s, p, o in g1])
        g2 = set()
        x2 = Ragged(">baz\nATGG\n>foo||z\nATGGG", na_str=[None])
        x2.connect(g2)
        s2 = sorted([(str(s), str(p), str(o)) for s, p, o in g2])
        self.assertEqual(s1, s2)


class TestSubtypeSelection(unittest.TestCase):
    def test_get_subtype_nothing_comes_from_nothing(self):
        # nothing comes from nothing and nothing ever will
        self.assertEqual(
            recipes._get_subtype(
                "whatever", [], [], gisaid_subtypes=[], genbank_subtypes=[]
            ),
            None,
        )

    def test_get_subtype_from_segments(self):
        self.assertEqual(
            recipes._get_subtype("whatever", ["H1"], ["N1"], [], []), "H1N1"
        )

        # spacing and capitolization shouldn't matter
        self.assertEqual(
            recipes._get_subtype("whatever", ["h1", "H1"], ["N1"], [], []), "H1N1"
        )
        self.assertEqual(
            recipes._get_subtype("whatever", ["h1 "], ["  n1 "], [], []), "H1N1"
        )

        # repetitions shouldn't matter
        self.assertEqual(
            recipes._get_subtype("whatever", ["H1", "H1"], ["N1"], [], []), "H1N1"
        )

        # but if they are different, then the "mixed" annotation should be returned
        self.assertEqual(
            recipes._get_subtype("whatever", ["H1", "H2"], ["N1"], [], []), "mixed"
        )

        # if either HA or NA is missing, the subtype is unknown
        self.assertEqual(
            recipes._get_subtype("whatever", ["H1"], [], [], []), None 
        )
        self.assertEqual(
            recipes._get_subtype("whatever", [], ["N1"], [], []), None
        )

        # if either HA or NA is missing, but genbank or gisaid have info, use their info
        # these subtype annotations could have been derived from PCR
        self.assertEqual(
            recipes._get_subtype("whatever", ["H1"], [], ["H1N1"], []), "H1N1"
        )
        self.assertEqual(
            recipes._get_subtype("whatever", [], ["N1"], [], ["H1N1"]), "H1N1"
        )
        self.assertEqual(
            recipes._get_subtype("whatever", [], ["N1"], ["H1N1"], ["H1N1"]), "H1N1"
        )

    def test_get_subtype_from_genbank_and_gisaid(self):
        # genbank or gisaid subtypes will be used if no clade info is available
        self.assertEqual(recipes._get_subtype("whatever", [], [], ["H1N1"], []), "H1N1")
        self.assertEqual(recipes._get_subtype("whatever", [], [], [], ["H1N1"]), "H1N1")

        # repetitions shouldn't matter
        self.assertEqual(
            recipes._get_subtype("whatever", [], [], ["H1N1", "H1N1"], ["H1N1"]), "H1N1"
        )
        self.assertEqual(
            recipes._get_subtype("whatever", [], [], ["H1N1"], ["H1N1", "H1N1"]), "H1N1"
        )
        self.assertEqual(
            recipes._get_subtype(
                "whatever", [], [], ["H1N1", "H1N1"], ["H1N1", "H1N1"]
            ),
            "H1N1",
        )

        # case and space shouldn't matter
        self.assertEqual(
            recipes._get_subtype("whatever", [], [], [" H1n1 ", " h1N1 "], []), "H1N1"
        )

        # variant tags and other annotations shouldn't matter
        self.assertEqual(
            recipes._get_subtype("whatever", [], [], ["H12avN12v"], ["H12N12pdm"]),
            "H12N12",
        )

        # multiple subtypes should yield mixed
        self.assertEqual(
            recipes._get_subtype("whatever", [], [], ["H1N1", "H3N2"], []), "mixed"
        )
        self.assertEqual(
            recipes._get_subtype("whatever", [], [], [], ["H1N1", "H3N2"]), "mixed"
        )
        self.assertEqual(
            recipes._get_subtype("whatever", [], ["H1N1"], ["H1N1", "H3N2"], []),
            "mixed",
        )
        self.assertEqual(
            recipes._get_subtype("whatever", [], [], ["H1N1", "H3N2"], ["H1N1"]),
            "mixed",
        )

        # order of search
        #  look first at the octoFLU inferred subtypes, use this even if gisaid of epiflu think it is mixed
        self.assertEqual(
            recipes._get_subtype("whatever", ["H4"], ["N6"], [], ["H1N1", "H3N2"]),
            "H4N6",
        )
        self.assertEqual(
            recipes._get_subtype(
                "whatever",
                ["H4"],
                ["N6"],
                gisaid_subtypes=["H1N1", "H3N2"],
                genbank_subtypes=[],
            ),
            "H4N6",
        )

        #  if there is no octoFLU info, and if genbank and gisaid disagree, go with genbank
        self.assertEqual(
            recipes._get_subtype(
                "whatever", [], [], gisaid_subtypes=["H4N6"], genbank_subtypes=["H3N2"]
            ),
            "H3N2",
        )


class TestConstellations(unittest.TestCase):
    def test_constellations_base_case(self):
        self.assertEqual(formatter._make_constellations([]), [])

    def test_constellations_regular(self):
        data = [
            # A PPPPPP
            ("A", "PB2", "pdm"),
            ("A", "PB1", "pdm"),
            ("A", "PA", "pdm"),
            ("A", "NP", "pdm"),
            ("A", "M", "pdm"),
            ("A", "NS", "pdm"),
            # B TTTTTT
            ("B", "PB2", "TRIG"),
            ("B", "PA", "TRIG"),
            ("B", "NP", "TRIG"),
            ("B", "PB1", "TRIG"),
            ("B", "M", "TRIG"),
            ("B", "NS", "TRIG"),
            # C VVVVVV
            ("C", "PB2", "LAIV"),
            ("C", "PA", "LAIV"),
            ("C", "NP", "LAIV"),
            ("C", "M", "LAIV"),
            ("C", "PB1", "LAIV"),
            ("C", "NS", "LAIV"),
            # D HHHHHH
            ("D", "PB1", "humanSeasonal"),
            ("D", "PA", "humanSeasonal"),
            ("D", "M", "humanSeasonal"),
            ("D", "NP", "humanSeasonal"),
            ("D", "NS", "humanSeasonal"),
            ("D", "PB2", "humanSeasonal"),
            # E PTHV-P
            ("E", "PB1", "TRIG"),
            ("E", "PA", "humanSeasonal"),
            ("E", "NP", "LAIV"),
            ("E", "NS", "pdm"),
            ("E", "PB2", "pdm"),
        ]
        out = [
            ("A", "PPPPPP"),
            ("B", "TTTTTT"),
            ("C", "VVVVVV"),
            ("D", "HHHHHH"),
            ("E", "PTHV-P"),
        ]
        self.assertEqual(formatter._make_constellations(data), out)

    def test_constellations_mixed(self):
        data = [
            # A PPPPPP
            ("A", "PB2", "pdm"),
            ("A", "PB1", "pdm"),
            ("A", "PA", "pdm"),
            ("A", "NP", "pdm"),
            ("A", "M", "pdm"),
            ("A", "NS", "pdm"),
            ("A", "NS", "TRIG"),
        ]
        out = [("A", "mixed")]
        self.assertEqual(formatter._make_constellations(data), out)

    def test_constellations_well_mixed(self):
        data = [
            # A PPPPPT
            ("A", "PB2", "pdm"),
            ("A", "PB1", "pdm"),
            ("A", "PA", "pdm"),
            ("A", "NP", "pdm"),
            ("A", "M", "pdm"),
            ("A", "NS", "TRIG"),
            ("A", "NS", "TRIG"), # duplicates are fine
        ]
        out = [("A", "PPPPPT")]
        self.assertEqual(formatter._make_constellations(data), out)

    def test_constellations_irregular(self):
        data = [
            # A PPPPPP
            ("A", "PB2", "pdm"),
            (
                "A",
                "PB1",
                "chocolate",
            ),  # FYI - unfortunately, it doesn't come in chocolate
            ("A", "NP", "pdm"),
            ("A", "NS", "TRIG"),
        ]
        out = [("A", "PX-P-T")]
        self.assertEqual(formatter._make_constellations(data), out)


if __name__ == "__main__":
    unittest.main()
