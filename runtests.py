#!/usr/bin/env python3

import src.classifiers.flucrew as ftok
from src.nomenclature import make_uri, make_usa_state_uri, make_country_uri
from src.classes import HomoList, Phrase, Datum, Ragged
from src.graph import showTriple
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


class TestBarcode(unittest.TestCase):
    def test_Barcode(self):
        self.assertEqual(ftok.Barcode("A01234567").clean, "A01234567")
        self.assertEqual(ftok.Barcode("bogus").clean, None)
        self.assertEqual(ftok.Barcode("K00869").clean, None)


class TestConstellation(unittest.TestCase):
    def test_Constellation(self):
        self.assertEqual(ftok.Constellation("TTPVVP").clean, "TTPVVP")
        self.assertEqual(ftok.Constellation("T-----").clean, "T-----")
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


class TestGisaidSeqid(unittest.TestCase):
    def test_GisaidSeqid(self):
        # no upper bound on integers
        self.assertEqual(
            ftok.GisaidSeqid("EPI_1234567890123").clean, "EPI1234567890123"
        )
        # underscore optional
        self.assertEqual(ftok.GisaidSeqid("EPI1234567890123").clean, "EPI1234567890123")
        # but at least 3
        self.assertEqual(ftok.GisaidSeqid("EPI_123").clean, "EPI123")
        # currently I don't allow fewer than 2 numbers
        self.assertEqual(ftok.GisaidSeqid("EPI_12").clean, None)
        self.assertEqual(ftok.GisaidSeqid("bogus").clean, None)


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
        self.assertEqual(ftok.GlobalClade("bogus").clean, None)


class TestSubtype(unittest.TestCase):
    def test_Subtype(self):
        self.assertEqual(ftok.Subtype("H1N1").clean, "H1N1")
        # or any number ...
        self.assertEqual(ftok.Subtype("H11N12").clean, "H11N12")
        # with possible variants
        self.assertEqual(ftok.Subtype("H1N1v").clean, "H1N1v")
        # no lower
        self.assertEqual(ftok.Subtype("h1n1").clean, None)
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
        self.assertEqual(ftok.InternalGene("NS1").clean, "NS1")
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
        self.assertEqual(ftok.SegmentName("NS1").clean, "NS1")
        self.assertEqual(ftok.SegmentName("H1").clean, "H1")
        self.assertEqual(ftok.SegmentName("HA").clean, "HA")
        self.assertEqual(ftok.SegmentName("NA").clean, "NA")
        self.assertEqual(ftok.SegmentName("N1").clean, "N1")
        self.assertEqual(ftok.SegmentName("bogus").clean, None)

    def test_AlternativeSegmentNames(self):
        self.assertEqual(ftok.SegmentName("MP").clean, "M")


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
        # support influenza A-D but not E (since there isn't one yet, and even
        # if there were, being pig people, we wouldn't care about it)
        self.assertEqual(ftok.Strain("A/asdf").clean, "A/asdf")
        self.assertEqual(ftok.Strain("B/asdf").clean, "B/asdf")
        self.assertEqual(ftok.Strain("C/asdf").clean, "C/asdf")
        self.assertEqual(ftok.Strain("D/asdf").clean, "D/asdf")
        self.assertEqual(ftok.Strain("E/asdf").clean, None)
        # allow space, but munge it to underscores
        self.assertEqual(ftok.Strain("A/asdf foo bar").clean, "A/asdf_foo_bar")
        # match does not include parentheses, these should be treated as
        # metadata outside the strain name
        self.assertEqual(ftok.Strain("A/asdf()").clean, None)
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
                    "http://www.w3.org/2002/07/owl#sameAs",
                    "https://flu-crew.org/id/a01234567",
                ),
                (
                    "https://flu-crew.org/id/a%2Fasdf%2Fa01234567%2Fsdf",
                    "https://flu-crew.org/term/strain_name",
                    "A/asdf/A01234567/sdf",
                ),
                (
                    "https://flu-crew.org/id/a01234567",
                    "https://flu-crew.org/term/barcode",
                    "A01234567",
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
        self.assertEqual(ftok.InternalGeneClade("VTX98").clean, "VTX98")
        self.assertEqual(ftok.InternalGeneClade("trig").clean, "trig")
        self.assertEqual(ftok.InternalGeneClade("pdm").clean, "pdm")
        self.assertEqual(ftok.InternalGeneClade("vtx98").clean, "vtx98")
        # don't accept random strings
        self.assertEqual(ftok.InternalGeneClade("bogus").clean, None)


class TestH1Clade(unittest.TestCase):
    def test_H1Clade(self):
        self.assertEqual(ftok.H1Clade("alpha").clean, "alpha")
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
            showTriple(["A01234567", "H1"]),
            [
                (
                    "https://flu-crew.org/id/a01234567",
                    "https://flu-crew.org/term/barcode",
                    "A01234567",
                ),
                (
                    "https://flu-crew.org/id/a01234567",
                    "https://flu-crew.org/term/ha",
                    "H1",
                ),
            ],
        )


class TestFasta(unittest.TestCase):
    def test_fasta(self):
        g = set()
        x = Ragged(">baz\nATGG\n>foo||z\nATGGG")
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


if __name__ == "__main__":
    unittest.main()
