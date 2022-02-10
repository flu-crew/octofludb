from __future__ import annotations
from typing import Optional, Callable, Union, List, Tuple, Set

import parsec as p
from octofludb.nomenclature import make_property
import rdflib
from rdflib.term import Node
import re
from rdflib.namespace import XSD


class Token:
    # The parser may either be a function or a parsec parser
    parser: Union[
        Callable[[Optional[str]], Optional[str]], p.Parser[str]
    ] = lambda x: None
    group: Optional[str] = None
    typename: Optional[str] = "auto"
    class_predicate: Optional[Node] = None

    def __init__(
        self, text: Optional[str], field: Optional[str] = None, na_str: List[str] = []
    ):
        self.match: Optional[str] = self.testOne(text, na_str=na_str)
        self.dirty: str = self.set_dirty(text, na_str)
        self.field: Optional[str] = field
        self.clean: Optional[str]
        if self.match is not None:
            self.clean = self.munge(self.match)
        else:
            self.clean = None

    def set_dirty(self, text: Optional[str], na_str: List[str]) -> str:
        if text is None:
            if na_str:
                return na_str[0]
            else:
                return ""
        else:
            return text

    def munge(self, text: str) -> str:
        return text

    def choose_field(self) -> Optional[str]:
        if self.field:
            return self.field
        else:
            return self.typename

    def as_uri(self) -> Optional[Node]:
        """
        Cast this token as a URI
        """
        return None  # default tokens cannot be URIs

    def as_predicate(self) -> Optional[Node]:
        field = self.choose_field()
        if field is None:
            return None
        else:
            return make_property(field)

    def as_object(self) -> Optional[Node]:
        return self.as_literal()

    def object_of(self, uri: Node) -> Set[Tuple[Node, Node, Node]]:
        g = set()
        predicate_node = self.as_predicate()
        object_node = self.as_object()
        if self.match and uri and predicate_node and object_node:
            g.add((uri, predicate_node, object_node))

        return g

    def as_literal(self) -> Optional[Node]:
        """
        Cast this token as a literal value if possible
        """
        if self.clean is None:
            return None
        else:
            return rdflib.Literal(self.clean)

    def add_triples(self) -> Set[Tuple[Node, Node, Node]]:
        """
        Add knowledge to the graph
        """
        return set()

    def relate(
        self, tokens: List[Token], levels: Optional[Set[str]] = set()
    ) -> Set[Tuple[Node, Node, Node]]:
        """
        Create links as desired between Tokens.
        """
        return set()

    def __str__(self):
        return self.clean

    def __bool__(self):
        return self.match is not None and self.match != ""

    @classmethod
    def testOne(cls, item: Optional[str], na_str: List[str] = []) -> Optional[str]:
        """
        The item is a member of this type. In the base case anything
        that can be turned into a string is a member.
        """
        if item in na_str or item is None:
            return None
        try:
            if isinstance(cls.parser, p.Parser):
                return cls.parser.parse_strict(item)
            else:
                return cls.parser(item)
        except p.ParseError:
            return None

    @classmethod
    def goodness(cls, items, na_str=[]):
        column_matches = [
            (cls.testOne(item=x, na_str=na_str) is not None)
            for x in items
            if not (x in na_str or x is None)
        ]
        if len(column_matches) > 0:
            return sum(column_matches) / len(column_matches)
        else:
            return 0


class Missing(Token):
    parser = lambda x: None
    typename = "missing"

    @classmethod
    def testOne(cls, item: Optional[str], na_str: List[str] = []) -> None:
        return None


class Unknown(Token):
    typename = "unknown"
    parser = lambda x: x

    @classmethod
    def testOne(cls, item: Optional[str], na_str: List[str] = []) -> Optional[str]:
        if item in na_str:
            return None
        else:
            return item


class String(Token):
    typename = "string"
    parser = lambda x: x

    # This should never be none so long as the parser succeeded
    def as_literal(self) -> Optional[Node]:
        if self.match:
            # this differs from Unknown in that no inference will be attempted
            return rdflib.Literal(self.dirty)
        else:
            return None

    @classmethod
    def testOne(cls, item: Optional[str], na_str: List[str] = []) -> Optional[str]:
        if item in na_str:
            return None
        else:
            return item


class Integer(Token):
    typename = "integer"
    parser = p.regex("[1-9]\\d*") ^ p.string("0")

    # This should never be none so long as the parser succeeded
    def as_literal(self) -> Optional[Node]:
        if self.match:
            return rdflib.Literal(self.clean, datatype=XSD.integer)
        else:
            return None


class Double(Token):
    typename = "double"
    parser = (
        p.regex("0\\.\\d+")
        ^ p.regex("[1-9]\\d*\\.\\d+")
        ^ p.regex("[1-9]\\d*")
        ^ p.string("0")
    )

    # This should never be none so long as the parser succeeded
    def as_literal(self) -> Optional[Node]:
        if self.match:
            return rdflib.Literal(self.clean, XSD.double)
        else:
            return None


class Boolean(Token):
    typename = "float"
    parser = p.regex("0|1|yes|no|true|false|y|n|t|f", flags=re.I)

    def munge(self, text):
        if text.lower() in ["1", "t", "true", "yes", "y"]:
            return "true"
        else:
            return "false"

    def as_literal(self) -> Optional[Node]:
        if self.clean in ["true", "false"]:
            return rdflib.Literal(self.clean, XSD.boolean)
        else:
            return None


class Ignore(Token):
    typename = "ignore_me"
    parser = lambda x: None

    @classmethod
    def testOne(cls, item: Optional[str], na_str: List[str] = []) -> None:
        return None


class Empty(Token):
    """If you want to throw out any field that is not recognized, make this the default"""

    typename = "empty"
    parser = p.regex(".*")

    def munge(self, text):
        return ""
