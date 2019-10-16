import parsec as p
from src.hash import chksum
from src.util import log
from src.domain.flu import SEGMENT
from rdflib import Literal
from collections import OrderedDict
import re

from src.domain.identifier import (
    p_global_clade,
    p_A0,
    p_tosu,
    p_gisaid_isolate,
    p_strain,
    p_gb,
    p_gisaid_seqid,
)

from src.domain.flu import (
    p_HA,
    p_NA,
    p_internal_gene,
    p_segment,
    p_segment_number,
    p_subtype,
    p_strain_obj,
    p_constellation,
    p_h1_clade,
    p_h3_clade,
    p_internal_gene_clade,
    p_n1_clade,
    p_n2_clade,
)

from src.domain.date import p_year, p_longyear, p_month, p_day, p_date, p_any_date
from src.domain.geography import (
    country_to_code,
    state_to_code,
    location_to_country_code,
)
from src.domain.animal import p_host
from src.domain.sequence import p_dnaseq, p_proseq

from src.token import Token, Unknown
from src.util import rmNone
from src.nomenclature import (
    make_uri,
    make_date,
    make_property,
    make_usa_state_uri,
    make_country_uri,
    P,
)

BARCODE_PAT = re.compile("A0\d{7}|\d+TOSU\d+|EPI_ISL_\d+")

class Country(Token):
    typename = "country"
    class_predicate = P.country

    def munge(self, text):
        return country_to_code(text)

    @classmethod
    def testOne(cls, item):
        return country_to_code(item)

    def as_uri(self):
        return make_country_uri(self.dirty)

    def object_of(self, g, uri):
        # I am allowing a link even when there was no match. This allows
        # unusual country names to be treated as countries when the context
        # suggests they are countries. But they do at least have to be
        # non-empty strings.
        if uri and self.dirty:
            g.add((uri, self.as_predicate(), self.as_uri()))


class CountryOrState(Token):
    """
    Maps countries, states, or major cities to the country code
    """

    typename = "country"
    class_predicate = P.country

    def munge(self, text):
        return location_to_country_code(text)

    @classmethod
    def testOne(cls, item):
        return location_to_country_code(item)

    def as_uri(self):
        return make_country_uri_from_code(self.clean)

    def object_of(self, g, uri):
        if uri and self.dirty:
            g.add((uri, self.as_predicate(), self.as_uri()))


class StateUSA(Token):
    typename = "state"
    class_predicate = P.state
    parser = state_to_code

    @classmethod
    def testOne(cls, item):
        return state_to_code(item)

    def object_of(self, g, uri):
        if uri and self.matches:
            g.add((uri, P.state, make_usa_state_uri(self.clean)))


class Date(Token):
    typename = "date"
    parser = p_any_date
    class_predicate = P.date

    def munge(self, text):
        return str(text)

    def as_literal(self):
        return make_date(self.dirty)


class Host(Token):
    typename = "host"
    parser = p_host

    def munge(self, text):
        return text.lower()


STRAIN_FIELDS = {
    "date",
    "country",
    "state",
    "host",
    "global_clade",
    "subtype",
    "barcode",
    "strain_name",
}

# --- strain tokens ---
class StrainToken(Token):
    group = "strain"

    def as_uri(self):
        return make_uri(self.clean)

    def _has_segment(self, tokens):
        for token in tokens:
            if token.group == "segment" or token.typename == "dnaseq":
                return True
        return None

    def relate(self, tokens, g, levels=None):
        if self.clean is None or not self.matches:
            return
        uri = self.as_uri()
        has_segment = self._has_segment(tokens)
        use_segment = (levels is None and has_segment) or (
            levels is not None and "segment" in levels and has_segment
        )
        g.add((uri, make_property(self.typename), self.as_literal()))
        for other in tokens:
            if not other.matches or other.clean == self.clean or other.clean is None:
                continue
            if other.group == "strain":
                g.add((uri, P.sameAs, other.as_uri()))
            elif other.group == "segment":
                g.add((uri, P.has_segment, other.as_uri()))
                if other.typename == "genbank":
                    g.add((uri, P.has_genbank, other.as_literal()))
            elif other.choose_field_name() in STRAIN_FIELDS:
                other.object_of(g, uri)
            elif not use_segment:
                other.object_of(g, uri)


class Barcode(StrainToken):
    typename = "barcode"
    parser = p_tosu ^ p_A0 ^ p_gisaid_isolate

    def munge(self, text):
        return text.upper()

    def add_triples(self, g):
        if self.clean:
            g.add((self.as_uri(), P.barcode, self.as_literal()))

class Strain(StrainToken):
    typename = "strain_name"
    parser = p_strain

    def munge(self, text):
        return text.replace(" ", "_")

    def add_triples(self, g):
        if self.clean:
            uri = self.as_uri()
            g.add((uri, P.strain_name, self.as_literal()))
            for el in self.clean.split("/"):
                barcode_match = re.fullmatch(BARCODE_PAT, el)
                state_str = StateUSA.parser(el)

                # some strain names contain a barcode, which is also a unique id
                if barcode_match is not None:
                    barcode = Barcode(barcode_match.group())
                    barcode.add_triples(g)
                    g.add((uri, P.sameAs, barcode.as_uri()))
                elif state_str is not None:
                    state = StateUSA(state_str)
                    state.object_of(g, uri)


# --- strain attributes ---
class StrainAttribute(Token):
    def relate(self, tokens, g, levels=None):
        for other in tokens:
            if other.group == "strain" and other.typename != self.typename:
                self.object_of(g, other.as_uri())


class Subtype(StrainAttribute):
    typename = "subtype"
    parser = p_subtype
    class_predicate = P.subtype


class Constellation(StrainAttribute):
    typename = "constellation"
    parser = p_constellation
    class_predicate = P.constellation


class GlobalClade(StrainAttribute):
    typename = "global_clade"
    parser = p_global_clade
    class_predicate = P.global_clade


class HA(StrainAttribute):
    typename = "HA"
    parser = p_HA
    class_predicate = P.ha_clade


class NA(StrainAttribute):
    typename = "NA"
    parser = p_NA
    class_predicate = P.na_clade


class InternalGene(StrainAttribute):
    typename = "internal_gene"
    parser = p_internal_gene


# --- strain tokens ---
class SegmentToken(Token):
    group = "segment"
    class_predicate = P.has_segment

    def as_uri(self):
        return make_uri(self.clean)

    def relate(self, tokens, g, levels=None):
        if not self.matches:
            return
        uri = self.as_uri()
        for other in tokens:
            if other.clean is None:
                continue
            if (
                other.matches
                and other.group == "segment"
                and other.typename != self.typename
            ):
                g.add(uri, P.sameAs, other.as_uri())
            elif not other.choose_field_name() in STRAIN_FIELDS:
                other.object_of(g, uri)


class Genbank(SegmentToken):
    typename = "genbank"
    parser = p_gb

    def munge(self, text):
        return text.upper()

    def add_triples(self, g):
        if self.clean:
            g.add((self.as_uri(), P.gb, self.as_literal()))


class GisaidSeqid(SegmentToken):
    typename = "gisaid_seqid"
    parser = p_gisaid_seqid

    def as_uri(self):
        return make_uri(self.clean)

    def munge(self, text):
        return text.upper().replace("_", "")

    def add_triples(self, g):
        if self.clean:
            g.add((self.as_uri(), P.gisaid_seqid, self.as_literal()))


# --- segment attributes ---
class SegmentAttribute(Token):
    def relate(self, tokens, g, levels=None):
        for other in tokens:
            if other.group == "segment":
                self.object_of(g, other.as_uri())


class SegmentName(SegmentAttribute):
    typename = "segment_name"
    parser = p_segment


class SegmentNumber(SegmentAttribute):
    typename = "segment_number"
    parser = p_segment_number

    def object_of(self, g, uri):
        if uri and self.matches:
            g.add((uri, P.segment_number, Literal(self.clean)))
            g.add((uri, P.segment_name, Literal(SEGMENT[int(self.clean) - 1])))


class SequenceToken(Token):
    group = "sequence"

    def munge(self, text):
        return re.sub("[^A-Z*]", "", text.upper())

    def as_uri(self):
        return make_uri(chksum(self.clean))

    def _has_segment(self, tokens):
        for token in tokens:
            if token.group == "segment":
                return True
        return None

    @classmethod
    def goodness(cls, items):
        matches = [
            bool((cls.testOne(item=x)) and len(str(x)) > 20) for x in rmNone(items)
        ]
        goodness = sum(matches) / len(matches)
        return goodness


class Dnaseq(SequenceToken):
    typename = "dnaseq"
    parser = p_dnaseq

    def object_of(self, g, uri):
        if uri and self.matches:
            g.add((uri, P.chksum, Literal(chksum(self.clean))))
            g.add((uri, P.dnaseq, Literal(self.clean)))

    def relate(self, tokens, g, levels=None):
        uri = self.as_uri()
        for other in tokens:
            if other.clean is None:
                continue
            elif other.group == "strain":
                g.add((other.as_uri(), P.has_segment, uri))
            elif not self._has_segment(tokens) and not other.typename in STRAIN_FIELDS:
                other.object_of(g, uri)


class Proseq(SequenceToken):
    typename = "proseq"
    parser = p_proseq

    def relate(self, tokens, g, levels=None):
        uri = self.as_uri()
        g.add((uri, P.proseq, Literal(self.clean)))
        has_segment = self._has_segment(tokens)
        for other in tokens:
            if other.clean is None:
                continue
            if other.group == "segment":
                g.add((other.as_uri(), P.has_feature, uri))
            elif other.group == "strain":
                if has_segment:
                    log("WARNING: I don't know how to connect a protein to a strain id")
            elif not other.choose_field_name() in STRAIN_FIELDS and not has_segment:
                other.object_of(g, uri)


class H1Clade(Token):
    typename = "h1_clade"
    parser = p_h1_clade


class H3Clade(Token):
    typename = "h3_clade"
    parser = p_h3_clade


class N1Clade(Token):
    typename = "n1_clade"
    parser = p_n1_clade


class N2Clade(Token):
    typename = "n2_clade"
    parser = p_n2_clade


class InternalGeneClade(Token):
    typename = "internal_gene_clade"
    parser = p_internal_gene_clade


allClassifiers = OrderedDict(
    [
        (c.typename, c)
        for c in [
            Genbank,
            Barcode,
            Constellation,
            Country,
            Date,
            GisaidSeqid,
            GlobalClade,
            Subtype,
            HA,
            NA,
            Host,
            InternalGene,
            SegmentName,
            SegmentNumber,
            Strain,
            StateUSA,
            InternalGeneClade,
            H1Clade,
            H3Clade,
            N1Clade,
            N2Clade,
            Dnaseq,
            Proseq,
            Unknown,
        ]
    ]
)
