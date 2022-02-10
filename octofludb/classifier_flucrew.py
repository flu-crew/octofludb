from __future__ import annotations
from typing import Set, List, Type, Tuple, Optional

from octofludb.hash import chksum
from octofludb.util import log, safeAdd
from octofludb.domain_flu import SEGMENT
from rdflib import Literal
from rdflib.term import Node
from collections import OrderedDict
import re

from octofludb.domain_identifier import (
    p_global_clade,
    p_A0,
    p_tosu,
    p_epi_isolate,
    p_strain,
    p_gb,
    p_epi_id,
)

from octofludb.domain_flu import (
    p_HA,
    p_NA,
    p_internal_gene,
    p_segment,
    p_segment_subtype,
    p_segment_number,
    p_subtype,
    p_constellation,
    p_h1_clade,
    p_h3_clade,
    p_internal_gene_clade,
    p_n1_clade,
    p_n2_clade,
)

from octofludb.domain_date import (
    p_any_date_str,
)
from octofludb.domain_geography import (
    country_to_code,
    state_to_code,
    location_to_country_code,
)
from octofludb.domain_animal import p_host
from octofludb.domain_sequence import p_dnaseq, p_proseq

from octofludb.token import Token, Unknown
from octofludb.nomenclature import (
    make_uri,
    make_date,
    make_property,
    make_usa_state_uri,
    make_literal,
    make_country_uri,
    make_country_uri_from_code,
    P,
)

BARCODE_PAT = re.compile("A0\d{7}|\d+TOSU\d+")


class Country(Token):
    typename = "country"
    class_predicate = P.country

    def munge(self, text):
        return country_to_code(text)

    @classmethod
    def testOne(cls, item, na_str=[]):
        if item in na_str or item is None:
            return None
        return country_to_code(item)

    def as_uri(self):
        return make_country_uri(self.dirty)

    def object_of(self, uri: Node) -> Set[Tuple[Node, Node, Node]]:
        # I am allowing a link even when there was no match. This allows
        # unusual country names to be treated as countries when the context
        # suggests they are countries. But they do at least have to be
        # non-empty strings.
        g = set()
        predicate_node = self.as_predicate()
        object_node = self.as_uri()
        if uri and self.dirty and predicate_node and object_node:
            g.add((uri, predicate_node, object_node))

        return g


class CountryOrState(Token):
    """
    Maps countries, states, or major cities to the country code
    """

    typename = "country"
    class_predicate = P.country

    def munge(self, text):
        return location_to_country_code(text)

    @classmethod
    def testOne(cls, item, na_str=[]):
        if item in na_str or item is None:
            return None
        return location_to_country_code(item)

    def as_uri(self):
        return make_country_uri_from_code(self.clean)

    def object_of(self, uri: Node) -> Set[Tuple[Node, Node, Node]]:
        predicate_node = self.as_predicate()
        object_node = self.as_uri()

        g = set()

        if uri and self.dirty and predicate_node and object_node:
            g.add((uri, predicate_node, object_node))

        return g


class StateUSA(Token):
    typename = "state"
    class_predicate = P.state
    parser = state_to_code

    @classmethod
    def testOne(cls, item, na_str=[]):
        if item in na_str or item is None:
            return None
        return state_to_code(item)

    def object_of(self, uri: Node) -> Set[Tuple[Node, Node, Node]]:

        g = set()

        if uri and self.match:
            g.add((uri, P.state, make_usa_state_uri(self.clean)))

        return g


class Date(Token):
    typename = "date"
    parser = p_any_date_str
    class_predicate = P.date

    def munge(self, text):
        return str(text)

    def as_literal(self) -> Optional[Node]:
        return make_date(self.dirty)


class Host(Token):
    typename = "host"
    parser = p_host

    def munge(self, text):
        return text.lower()


STRAIN_FIELDS = {
    "date",
    "submission_date",
    "collection_date",
    "country",
    "state",
    "host",
    "global_clade",
    "subtype",
    "barcode",
    "strain_name",
    "gisaid_strain_name",
}

# --- strain tokens ---
class StrainToken(Token):
    group = "strain"

    def as_uri(self):
        return make_uri(self.clean)

    def munge(self, text):
        return text.replace(" ", "_")

    def _has_segment(self, tokens):
        for token in tokens:
            if token.group == "segment" or token.typename == "dnaseq":
                return True
        return None

    def relate(
        self, tokens: List[Token], levels: Optional[Set[str]] = None
    ) -> Set[Tuple[Node, Node, Node]]:
        g: Set[Tuple[Node, Node, Node]] = set()
        if self.clean is not None and self.match:
            uri = self.as_uri()
            has_segment = self._has_segment(tokens)
            use_segment = (levels is None and has_segment) or (
                levels is not None and "segment" in levels and has_segment
            )
            if self.typename is not None:
                safeAdd(g, uri, make_property(self.typename), self.as_literal())
            for other in tokens:
                if not other.match or other.clean == self.clean or other.clean is None:
                    continue
                if other.group == "segment":
                    safeAdd(g, uri, P.has_segment, other.as_uri())
                elif other.choose_field() in STRAIN_FIELDS:
                    g.update(other.object_of(uri))
                elif not use_segment:
                    g.update(other.object_of(uri))
        return g


class Isolate(StrainToken):
    typename = "isolate_id"
    parser = p_epi_isolate

    def munge(self, text):
        return text.upper()


class Barcode(StrainToken):
    typename = "barcode"
    parser = p_tosu ^ p_A0

    def munge(self, text):
        return text.upper()

    def add_triples(self) -> Set[Tuple[Node, Node, Node]]:
        g: Set[Tuple[Node, Node, Node]] = set()
        if self.clean:
            safeAdd(g, self.as_uri(), P.barcode, self.as_literal())
        return g


class Strain(StrainToken):
    typename = "strain_name"
    parser = p_strain

    def munge(self, text):
        return text.replace(" ", "_")

    def add_triples(self) -> Set[Tuple[Node, Node, Node]]:
        g: Set[Tuple[Node, Node, Node]] = set()
        if self.clean:
            uri = self.as_uri()
            safeAdd(g, uri, P.strain_name, self.as_literal())
            for el in self.clean.split("/"):
                barcode_match = re.fullmatch(BARCODE_PAT, el)
                state_str = StateUSA.parser(el)

                # some strain names contain a barcode, which is also a unique id
                if barcode_match is not None:
                    safeAdd(g, uri, P.strain_name, self.as_literal())
                    g.add((uri, P.barcode, make_literal(barcode_match[0])))
                elif state_str is not None:
                    state = StateUSA(state_str)
                    g.update(state.object_of(uri))

        return g


# --- strain attributes ---
class StrainAttribute(Token):
    def relate(
        self, tokens: List[Token], levels: Optional[Set[str]] = set()
    ) -> Set[Tuple[Node, Node, Node]]:
        g: Set[Tuple[Node, Node, Node]] = set()
        for other in tokens:
            if other.group == "strain" and other.typename != self.typename:
                other_uri = other.as_uri()
                if other_uri is not None:
                    g.update(self.object_of(other_uri))
        return g


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

    def as_uri(self) -> Optional[Node]:
        return make_uri(self.clean)

    def relate(
        self, tokens: List[Token], levels: Optional[Set[str]] = set()
    ) -> Set[Tuple[Node, Node, Node]]:
        g: Set[Tuple[Node, Node, Node]] = set()
        if not self.match:
            return g
        uri = self.as_uri()
        for other in tokens:
            if other.clean is None:
                continue
            if (
                other.match
                and other.group == "segment"
                and other.typename != self.typename
            ):
                safeAdd(g, uri, P.sameAs, other.as_uri())
            elif (
                not other.choose_field() in STRAIN_FIELDS and other.typename is not None
            ):
                if uri is not None:
                    g.update(other.object_of(uri))
        return g


class Genbank(SegmentToken):
    typename = "genbank_id"
    parser = p_gb

    def munge(self, text):
        return text.upper()

    def add_triples(self) -> Set[Tuple[Node, Node, Node]]:
        g: Set[Tuple[Node, Node, Node]] = set()
        if self.clean:
            safeAdd(g, self.as_uri(), P.gb, self.as_literal())
        return g


class EpiSeqid(SegmentToken):
    typename = "epi_id"
    parser = p_epi_id

    def as_uri(self) -> Optional[Node]:
        return make_uri(self.clean)

    def munge(self, text):
        return text.upper().replace("_", "")

    def add_triples(self) -> Set[Tuple[Node, Node, Node]]:
        g: Set[Tuple[Node, Node, Node]] = set()
        if self.clean:
            safeAdd(g, self.as_uri(), P.epi_id, self.as_literal())
        return g


# --- segment attributes ---
class SegmentAttribute(Token):
    def relate(
        self, tokens: List[Token], levels: Optional[Set[str]] = set()
    ) -> Set[Tuple[Node, Node, Node]]:
        g = set()
        for other in tokens:
            if other.group == "segment":
                other_uri = other.as_uri()
                if other_uri is not None:
                    g.update(self.object_of(other_uri))
        return g


class SegmentName(SegmentAttribute):
    typename = "segment_name"
    parser = p_segment


class SegmentSubtype(SegmentAttribute):
    typename = "segment_subtype"
    parser = p_segment_subtype


class SegmentNumber(SegmentAttribute):
    typename = "segment_number"
    parser = p_segment_number

    def object_of(self, uri: Node) -> Set[Tuple[Node, Node, Node]]:
        g: Set[Tuple[Node, Node, Node]] = set()
        if uri and self.match and self.clean is not None:
            g.add((uri, P.segment_number, Literal(self.clean)))
            g.add((uri, P.segment_name, Literal(SEGMENT[int(self.clean) - 1])))
        return g


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
    def goodness(cls, items, na_str=[]):
        column_matches = [
            bool(cls.testOne(item=x, na_str=na_str)) and len(str(x)) > 20
            for x in items
            if not (x in na_str or x is None)
        ]
        if len(items) > 0:
            goodness = sum(column_matches) / len(items)
        else:
            goodness = 0
        return goodness


class Dnaseq(SequenceToken):
    typename = "dnaseq"
    parser = p_dnaseq

    def object_of(self, uri: Node) -> Set[Tuple[Node, Node, Node]]:
        g: Set[Tuple[Node, Node, Node]] = set()
        if uri and self.match:
            g.add((uri, P.chksum, Literal(chksum(self.clean))))
            g.add((uri, P.dnaseq, Literal(self.clean)))
        return g

    def relate(
        self, tokens: List[Token], levels: Optional[Set[str]] = set()
    ) -> Set[Tuple[Node, Node, Node]]:
        g: Set[Tuple[Node, Node, Node]] = set()
        uri = self.as_uri()
        for other in tokens:
            if other.clean is None:
                continue
            elif other.group == "strain":
                safeAdd(g, other.as_uri(), P.has_segment, uri)
            elif (
                not self._has_segment(tokens)
                and other.typename not in STRAIN_FIELDS
                and uri is not None
            ):
                g.update(other.object_of(uri))
        return g


class Proseq(SequenceToken):
    typename = "proseq"
    parser = p_proseq

    def relate(
        self, tokens: List[Token], levels: Optional[Set[str]] = set()
    ) -> Set[Tuple[Node, Node, Node]]:
        g: Set[Tuple[Node, Node, Node]] = set()
        uri = self.as_uri()
        safeAdd(g, uri, P.proseq, make_literal(self.clean, infer=False))
        has_segment = self._has_segment(tokens)
        for other in tokens:
            if other.clean is None:
                continue
            if other.group == "segment":
                safeAdd(g, other.as_uri(), P.has_feature, uri)
            elif other.group == "strain":
                if has_segment:
                    log("WARNING: I don't know how to connect a protein to a strain id")
            elif not other.choose_field() in STRAIN_FIELDS and not has_segment:
                if uri is not None:
                    g.update(other.object_of(uri=uri))
        return g


class H1Clade(Token):
    typename = "h1_clade"
    parser = p_h1_clade


class H3Clade(Token):
    typename = "h3_clade"
    parser = p_h3_clade


class US_Clade(Token):
    typename = "us_clade"
    parser = p_h1_clade ^ p_h3_clade


class N1Clade(Token):
    typename = "n1_clade"
    parser = p_n1_clade


class N2Clade(Token):
    typename = "n2_clade"
    parser = p_n2_clade


class InternalGeneClade(Token):
    typename = "internal_gene_clade"
    parser = p_internal_gene_clade


allClassifiers: OrderedDict[str, Type[Token]] = OrderedDict(
    [
        (c.typename, c)
        for c in [
            Isolate,
            Genbank,
            Barcode,
            Constellation,
            Country,
            Date,
            EpiSeqid,
            GlobalClade,
            Subtype,
            SegmentName,
            SegmentSubtype,
            Host,
            InternalGene,
            SegmentNumber,
            Strain,
            StateUSA,
            InternalGeneClade,
            H1Clade,
            H3Clade,
            US_Clade,
            N1Clade,
            N2Clade,
            Dnaseq,
            Proseq,
            Unknown,
        ]
        if c.typename is not None
    ]
)
