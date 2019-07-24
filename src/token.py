import parsec as p
from src.nomenclature import (
    make_property,
    make_literal,
    define_subproperty,
)
import rdflib
import sys
from src.util import (rmNone)

class Token:
    parser = None
    group = None
    typename = "auto" 
    class_predicate = None

    def __init__(self, text, field_name=None):
        self.matches = self.testOne(text)
        self.dirty = text
        self.field_name=field_name
        if self.matches:
            self.clean = self.munge(text)
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
        return None # default tokens cannot be URIs

    def as_predicate(self):
        return make_property(self.choose_field_name().lower())

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
        if self.field_name and self.field_name != self.typename and self.class_predicate and self.matches:
            define_subproperty(self.as_predicate(), self.class_predicate, g)


    def relate(self, fields, g):
        """
        Create links as desired between Tokens.
        """
        pass

    def __str__(self):
        return self.clean

    def __bool__(self):
        return self.matches

    @classmethod
    def testOne(cls, item):
        """
        The item is a member of this type. In the base case anything
        that can be turned into a string is a member.
        """
        if item is None:
            return False
        try:
            result = cls.parser.parse_strict(item)
            return bool(result)
        except p.ParseError:
            return False
        return True

    @classmethod
    def goodness(cls, items):
        matches = [cls.testOne(item=x) for x in rmNone(items)]
        goodness = sum(matches) / len(matches)
        return goodness


class Missing(Token):
    parser = None
    typename = "missing" 


class Unknown(Token):
    typename = "unknown"
    parser = p.regex(".*")

    @classmethod
    def testOne(cls, item):
        return True

class Empty(Token):
    """ If you want to throw out any field that is not recognized, make this the default """ 
    typename = "empty"
    parser = p.regex(".*")

    def munge(self, text):
        return ""
