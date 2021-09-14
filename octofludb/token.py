import parsec as p
from octofludb.nomenclature import make_property, make_literal, define_subproperty
import rdflib
import sys
import re
import math
from octofludb.util import rmNone, log
from rdflib.namespace import XSD


class Token:
    parser = None
    group = None
    typename = "auto"
    class_predicate = None

    def __init__(self, text, field_name=None, na_str=[None]):
        self.matches = self.testOne(text, na_str=na_str)
        self.dirty = text
        self.field_name = field_name
        if self.matches is not None:
            self.clean = self.munge(self.matches)
        else:
            self.clean = None

    def munge(self, text):
        return text

    def choose_field_name(self):
        if self.field_name:
            return self.field_name
        else:
            return self.typename

    def as_uri(self):
        """
        Cast this token as a URI
        """
        return None  # default tokens cannot be URIs

    def as_predicate(self):
        return make_property(self.choose_field_name())

    def as_object(self):
        return self.as_literal()

    def object_of(self, g, uri):
        if uri and self.matches:
            g.add((uri, self.as_predicate(), self.as_object()))

    def as_literal(self):
        """
        Cast this token as a literal value
        """
        return rdflib.Literal(self.clean)

    def add_triples(self, g):
        """
        Add knowledge to the graph
        """
        return None
        # # FIXME: the following code unifies fields of the same type, but it can go too far
        #  if (
        #      self.field_name
        #      and self.field_name != self.typename
        #      and self.class_predicate
        #      and self.matches
        #  ):
        #      define_subproperty(self.as_predicate(), self.class_predicate, g)

    def relate(self, fields, g, levels=None):
        """
        Create links as desired between Tokens.
        """
        pass

    def __str__(self):
        return self.clean

    def __bool__(self):
        return self.matches is not None and self.matches != ""

    @classmethod
    def testOne(cls, item, na_str=[None]):
        """
        The item is a member of this type. In the base case anything
        that can be turned into a string is a member.
        """
        if item in na_str:
            return None
        try:
            return cls.parser.parse_strict(item)
        except p.ParseError:
            return None

    @classmethod
    def goodness(cls, items, na_str=[None]):
        matches = [
            (cls.testOne(item=x, na_str=na_str) != None)
            for x in items
            if x not in na_str
        ]
        if len(matches) > 0:
            return sum(matches) / len(matches)
        else:
            return 0


class Missing(Token):
    parser = lambda x: None
    typename = "missing"

    @classmethod
    def testOne(cls, item, na_str=[None]):
        return None


class Unknown(Token):
    typename = "unknown"
    parser = lambda x: x

    @classmethod
    def testOne(cls, item, na_str=[None]):
        try:
            if math.isnan(item):
                return None
        except TypeError:
            pass
        if item in na_str:
            return None
        else:
            return item


class Integer(Token):
    typename = "integer"
    parser = p.regex("[1-9]\\d*") ^ p.string("0")

    def as_literal(self):
        return rdflib.Literal(self.clean, datatype=XSD.integer)


class Double(Token):
    typename = "double"
    parser = (
        p.regex("0\\.\\d+")
        ^ p.regex("[1-9]\\d*\\.\\d+")
        ^ p.regex("[1-9]\\d*")
        ^ p.string("0")
    )

    def as_literal(self):
        return rdflib.Literal(self.clean, XSD.double)


class Boolean(Token):
    typename = "float"
    parser = p.regex("0|1|yes|no|true|false|y|n|t|f", flags=re.I)

    def munge(self, text):
        if text.lower() in ["1", "t", "true", "yes", "y"]:
            return "true"
        else:
            return "false"

    def as_literal(self):
        return rdflib.Literal(self.clean, XSD.boolean)


class Ignore(Token):
    typename = "ignore_me"
    parser = lambda x: None

    @classmethod
    def testOne(cls, item, na_str=[None]):
        return None


class Empty(Token):
    """If you want to throw out any field that is not recognized, make this the default"""

    typename = "empty"
    parser = p.regex(".*")

    def munge(self, text):
        return ""
