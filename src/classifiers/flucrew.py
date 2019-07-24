import parsec as p
from src.hash import chksum
from src.util import log
from rdflib import Literal

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
)

from src.domain.date import (
    p_year,
    p_longyear,
    p_month,
    p_day,
    p_date,
    p_any_date,
)

from src.domain.geography import (
    country_to_code,
    state_to_code,
)

from src.domain.animal import (
    p_host,
)

from src.domain.sequence import (
    p_dnaseq,
    p_proseq,
)

from src.token import Token
from src.util import rmNone
from src.nomenclature import (
    make_uri,       
    make_date,
    make_property,
    make_usa_state_uri,
    P,
)

class Country(Token):
    typename = "country"
    class_predicate = P.country

    def munge(self, text):
        return country_to_code(text)

    @classmethod
    def testOne(cls, item):
        return bool(country_to_code(item))

    def as_uri(self):
        return make_country_uri(self.clean)

class StateUSA(Token):
    typename = "state"
    class_predicate = P.state

    def munge(self, text):
        return state_to_code(text)

    @classmethod
    def testOne(cls, item):
        return bool(state_to_code(item))

    def object_of(self, g, uri):
        if uri and self.matches:
            g.add((uri, P.state, make_usa_state_uri(self.clean)))



class Date(Token):
    typename = "date"
    parser = p_any_date
    class_predicate = P.date

    def as_literal(self):
        return make_date(self.clean)


class Host(Token):
    typename = "host"
    parser = p_host

    def munge(self, text):
        return text.lower()

STRAIN_FIELDS = {"date", "country", "state", "host"}

# --- strain tokens ---
class StrainToken(Token):
    group = "strain_id"

    def as_uri(self):
        return make_uri(self.clean)

    def _has_segment(self, fields):
        for v in fields.values():
            if v.group == "segment_id" or v.typename == "dnaseq":
                return True
        return None

    def relate(self, fields, g):
        if self.clean is None or not self.matches: 
            return
        uri = self.as_uri()
        has_segment = self._has_segment(fields)
        g.add((uri, make_property(self.typename), self.as_literal()))
        for (name, other) in fields.items():
            if not other.matches or other.clean == self.clean or other.clean is None:
                continue
            if other.group == "strain_id":
                g.add((uri, P.sameAs, other.as_uri()))
            elif other.group == "segment_id":
                g.add((uri, P.has_segment, other.as_uri()))
            elif other.typename in STRAIN_FIELDS:
                other.object_of(g, uri)
            elif not has_segment:
                other.object_of(g, uri)

class Barcode(StrainToken):
    typename = "barcode"
    parser = p_tosu ^ p_A0 ^ p_gisaid_isolate

    def munge(self, text):
        return text.upper()

class Strain(StrainToken):
    typename = "strain_name"
    parser = p_strain

    def munge(self, text):
        return text.replace(" ", "_")


# --- strain attributes ---
class StrainAttribute(Token):
    def relate(self, fields, g):
        for (name, other) in fields.items():
            if other.group == "strain_id" and other.typename != self.typename:
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
    group = "segment_id"
    class_predicate = P.has_segment

    def as_uri(self):
        return make_uri(self.clean)

    def relate(self, fields, g):
        if not self.matches:
            return
        uri = self.as_uri()
        for (name, other) in fields.items():
            if other.matches and other.group == "segment_id" and other.typename != self.typename:
                g.add(uri, P.sameAs, other.as_uri())
            elif not other.typename in STRAIN_FIELDS: 
                other.object_of(g, uri)

class Genbank(SegmentToken):
    typename = "genbank"
    parser = p_gb

    def munge(self, text):
        return text.upper()

class GisaidSeqid(SegmentToken):
    typename = "gisaid_seqid"
    parser = p_gisaid_seqid

    def munge(self, text):
        return text.upper()


# --- segment attributes ---
class SegmentAttribute(Token):
    def relate(self, fields, g):
        for (name, other) in fields.items():
            if other.group == "segment_id":
                self.object_of(g, other.as_uri())

class Segment(SegmentAttribute):
    typename = "segment"
    parser = p_segment

class SegmentNumber(SegmentAttribute):
    typename = "segment_number"
    parser = p_segment_number

class SequenceToken(Token):
    group = "sequence"

    def munge(self, text):
        return text.upper().replace(" ", "")

    def as_uri(self):
        return make_uri(chksum(self.clean)) 

    @classmethod
    def goodness(cls, items):
        matches = [(cls.testOne(item=x) and len(str(x)) > 20) for x in rmNone(items)]
        goodness = sum(matches) / len(matches)
        return goodness


class Dnaseq(SequenceToken):
    typename = "dnaseq"
    parser = p_dnaseq

    def relate(self, fields, g):
        uri = self.as_uri()
        g.add((uri, P.dnaseq, Literal(self.clean)))
        for other in fields.values():
            if other.group == "segment_id":
                g.add((other.as_uri(), P.sameAs, uri))
            elif other.group == "strain_id":
                g.add((other.as_uri(), P.has_segment, uri))
            elif not other.typename in STRAIN_FIELDS: 
                other.object_of(g, uri)

class Proseq(SequenceToken):
    typename = "proseq"
    parser = p_proseq

    def _has_segment(self, fields):
        for v in fields.values():
            if v.group == "segment_id":
                return True
        return None

    def relate(self, fields, g):
        uri = self.as_uri()
        g.add((uri, P.proseq, Literal(self.clean)))
        has_segment = self._has_segment(fields)
        for other in fields.values():
            if other.group == "segment_id":
                g.add((other.as_uri(), P.has_feature, uri))
            elif other.group == "strain_id":
                if has_segment:
                    log("WARNING: I don't know how to connect a protein to a strain id")
            elif not other.typename in STRAIN_FIELDS and not has_segment: 
                other.object_of(g, uri)

allClassifiers = dict(
  "barcode" = Barcode,
  "constellation" = Constellation,
  "country" = Country,
  "date" = Date,
  "genbank" = Genbank,
  "gisaidSeqid" = GisaidSeqid,
  "globalClade" = GlobalClade,
  "subtype" = Subtype,
  "HA" = HA,
  "NA" = NA,
  "host" = Host,
  "internalGene" = InternalGene,
  "segment" = Segment,
  "segmentNumber" = SegmentNumber,
  "strain" = Strain,
  "state" = StateUSA,
  "dnaseq" = Dnaseq,
  "proseq" = Proseq,
  "default" = Unknown,
)
