from __future__ import annotations
from typing import Set, Dict, List, Optional, Any, Type, TextIO, Tuple, Union

import parsec
from octofludb.classifier_flucrew import allClassifiers
from octofludb.token import Token, Unknown, Missing
from octofludb.util import strOrNone, log, concat, die
from octofludb.nomenclature import make_tag_uri, make_literal, P
import xlrd  # type: ignore
import pandas as pd  # type: ignore
import octofludb.colors as colors
import datetime as datetime
from rdflib.term import Node
from tqdm import tqdm  # type: ignore
from collections import OrderedDict


def get_filename(fh: Union[str, TextIO]) -> Optional[str]:
    if isinstance(fh, str):
        return None
    else:
        return fh.name


def updateClassifiers(
    classifiers: OrderedDict[str, Type[Token]], include: Set[str], exclude: Set[str]
) -> List[Type[Token]]:
    keys = list(classifiers.keys())
    for classifier in keys:
        if classifier in exclude:
            classifiers.pop(classifier)
        if classifier in include:
            classifiers.pop(classifier)
    return list(classifiers.values())


class Interpreter:
    def __init__(
        self,
        data: Any,
        field: Optional[str] = None,
        tag: Optional[str] = None,
        classifiers: OrderedDict[str, Type[Token]] = allClassifiers,
        default_classifier: Type[Token] = Unknown,
        include: Set[str] = set(),
        exclude: Set[str] = set(),
        levels: Optional[Set[str]] = None,
        na_str: List[str] = [],
        log: bool = False,
    ):
        self.tag = tag
        self.levels = levels
        self.na_str = na_str
        self.classifiers = updateClassifiers(classifiers, include, exclude)
        self.default_classifier = default_classifier
        if log:
            self.log()
        self.field = field
        self.data = self.cast(data)

    def cast(self, data):
        raise NotImplementedError

    def load(self, g):
        raise NotImplementedError

    def summarize(self):
        raise NotImplementedError

    def log(self):
        log("Parsing with the following tokens:")
        for classifier in self.classifiers:
            log(f"  {colors.good(classifier.typename)}")
        if self.tag:
            log(f"Tagging as '{self.tag}'")
        else:
            log(f"{colors.bad('No tag given')}")


class Datum(Interpreter):
    """
    Interpret a single word. This should not be used much.
    """

    def cast(self, data: str) -> Token:
        if data == "":
            return Missing(data, na_str=self.na_str)
        for classifier in self.classifiers:
            token = classifier(data, field=self.field, na_str=self.na_str)
            if token:
                return token
        return self.default_classifier(data, field=self.field, na_str=self.na_str)

    def summarize(self):
        log(f"typename: {self.data.typename}")
        log(f"field: {self.data.field}")
        log(f"value: {self.data.dirty}")
        log(f"munged: {self.data.clean}")

    def __str__(self):
        return str(self.data.clean)


def addTag(
    tag: Optional[str], filename: Optional[str]
) -> Tuple[Optional[Node], Set[Tuple[Node, Node, Node]]]:
    """
    Add tag info to the triple set and return the tag URI
    """

    g: Set[Tuple[Node, Node, Node]] = set()

    if tag:
        taguri = make_tag_uri(tag)

        g.add((taguri, P.name, make_literal(tag)))
        g.add((taguri, P.time, make_literal(datetime.datetime.now())))
        if filename is not None and filename != "":
            g.add((taguri, P.file, make_literal(filename)))
    else:
        taguri = None
        g = set()
    return (taguri, g)


class HomoList(Interpreter):
    """
    Interpret a list of items assumed to be of the same type
    """

    def cast(self, data: List[str]) -> List[Token]:
        for classifier in self.classifiers:
            if classifier.goodness(data, na_str=self.na_str) > 0.8:
                c = classifier
                break
        else:
            c = self.default_classifier
        return [c(x, field=self.field, na_str=self.na_str) for x in data]

    def connect(self) -> Set[Tuple[Node, Node, Node]]:

        triples = addTag(tag=self.tag, filename=None)[1]

        for token in self.data:
            if token.clean is None:
                continue
            triples.update(token.add_triples())

        return triples

    def __str__(self) -> str:

        return str([t.clean for t in self.data])


class ParsedPhraseList(Interpreter):
    def __init__(
        self,
        text: Union[str, TextIO],
        field: Optional[str] = None,
        tag: Optional[str] = None,
        classifiers: OrderedDict[str, Type[Token]] = allClassifiers,
        default_classifier: Type[Token] = Unknown,
        include: Set[str] = set(),
        exclude: Set[str] = set(),
        levels: Optional[Set[str]] = None,
        na_str: List[str] = [],
        log: bool = False,
    ):
        self.classifiers = updateClassifiers(classifiers, include, exclude)
        self.tag = tag
        self.levels = levels
        self.na_str = na_str
        if log:
            self.log()
        self.text = text
        self.default_classifier = default_classifier
        self.data = self.cast(self.parse(text))

    def parse(self, text):
        raise NotImplementedError

    def connect(self) -> Set[Tuple[Node, Node, Node]]:
        log("Making triples")

        taguri, triples = addTag(tag=self.tag, filename=get_filename(self.text))
        for (i, phrase) in enumerate(tqdm(self.data)):
            triples.update(phrase.connect(taguri=taguri))
        return triples


def tabularTyping(
    data: Dict[str, List[Optional[str]]],
    levels: Optional[Set[str]] = None,
    na_str: List[str] = [],
) -> List[Phrase]:
    cols = []
    if not data:
        return []
    for k, v in data.items():
        hl = HomoList(v, field=k, na_str=na_str).data
        if len(hl) > 0:
            log(f" - '{k}':{colors.good(hl[0].typename)}")
        else:
            log(f"{colors.bad('Warning:')} no data")
        cols.append(hl)
    phrases = [
        Phrase([col[i] for col in cols], levels=levels) for i in range(len(cols[0]))
    ]
    return phrases


def headlessTabularTyping(
    data: List[List[str]], levels: Optional[Set[str]] = None, na_str: List[str] = []
):
    cols = []
    if not data:
        return []
    for (i, xs) in enumerate(data):
        hl = HomoList(xs, na_str=na_str).data
        log(f" - 'X{i}':{colors.good(hl[0].typename)}")
        cols.append(hl)
    phrases = [
        Phrase([col[i] for col in cols], levels=levels) for i in range(len(cols[0]))
    ]
    return phrases


class Table(ParsedPhraseList):
    """
    Parse a table.

    The table may be a TAB-delimited file or an excel file. It is assumed to
    have a header.
    """

    def __init__(self, *args, **kwargs):
        self.header: List[str] = []
        super().__init__(*args, **kwargs)

    def cast(self, data: Dict[str, List[Optional[str]]]) -> List[Phrase]:
        return tabularTyping(data, levels=self.levels, na_str=self.na_str)

    def parse(self, text: Union[str, TextIO]) -> Dict[str, List[Optional[str]]]:
        """
        Make a dictionary with column name as key and list of strings as value.
        Currently only Excel is supported.
        """
        if isinstance(text, TextIO):
            try:
                data = self._parse_excel(text)
            except:
                data = self._parse_table(text)
        else:
            data = self._parse_table(text)
        return data

    def _parse_excel(self, text: TextIO) -> Dict[str, List[Optional[str]]]:
        try:
            log(f"Reading {text.name} as excel file ...")
            d = pd.read_excel(text.name)
            self.header = list(d.columns)
            # create a dictionary of List(str) with column names as keys
            return {c: [strOrNone(x) for x in d[c]] for c in d}
        except xlrd.biffh.XLRDError as e:
            log(f"Could not parse '{text.name}' as an excel file")
            raise e
        return d

    def _parse_table(
        self, text: Union[str, TextIO], delimiter: str = "\t"
    ) -> Dict[str, List[Optional[str]]]:
        if isinstance(text, str):
            log("Reading raw string as tab-delimited file ...")
            lines = [s.rstrip() for s in text.split("\n")]
        else:
            log(f"Reading '{text.name}' as tab-delimited file ...")
            lines = text.readlines()

        rows = [r.split(delimiter) for r in lines]
        if len(rows) == 0:
            die("Empty input table, it should at least have a header")
        else:
            self.header = [c.strip() for c in rows[0]]
            indices = range(len(self.header))
            rows = rows[1:]
            columns = {
                self.header[i]: [strOrNone(r[i].strip()) for r in rows] for i in indices
            }
            return columns


class Ragged(ParsedPhraseList):
    """
    Interpret a ragged list of lists (e.g. a fasta file). For now I will parse
    each sublist as a Phrase. I could probable extract some type information
    from comparing phrases.
    """

    def cast(self, data: List[List[str]]) -> List[Phrase]:
        # If all entries have the same number of entries, I treat them as a
        # table. Then I can use column-based type inference.
        if len({len(xs) for xs in data}) == 1:
            N = len(data[0])
            log(f"Applying column type inference (all headers have {N-1} fields)")
            tabular_data = [[row[i] for row in data] for i in range(N)]
            return headlessTabularTyping(
                tabular_data, levels=self.levels, na_str=self.na_str
            )
        else:
            return [
                Phrase(
                    [Datum(x, na_str=self.na_str).data for x in row], levels=self.levels
                )
                for row in data
            ]

    def parse(self, text: Union[str, TextIO]) -> List[List[str]]:
        """
        Return a list of lists of strings. Currently only FASTA is supported.
        """
        return self._parse_fasta(text, sep="|")

    def _parse_fasta(self, text: Union[str, TextIO], sep: str = "|") -> List[List[str]]:
        """
        Parse a fasta file. The header is split into fields on 'sep'. The
        sequence is added as a final field.
        """
        p_header = parsec.string(">") >> parsec.regex("[^\n\r]*") << parsec.spaces()
        p_seq = (
            parsec.sepBy1(
                parsec.regex("[^>\n\r]*"), sep=parsec.regex("[\r\n\t ]+")
            ).parsecmap(concat)
            << parsec.spaces()
        )
        p_entry = p_header + p_seq
        p_fasta = parsec.many1(p_entry)

        if isinstance(text, str):
            log("Reading raw string as a fasta data:")
            fasta_str = text
        else:
            log(f"Reading '{text.name}' as a fasta file:")
            fasta_str = text.read()

        entries = p_fasta.parse(fasta_str)

        row = [h.split(sep) + [q] for (h, q) in entries]
        return row


#  class HetList(Interpreter):
#      """
#      Interpret a list of items of different types
#      """
#      def cast(self, items):
#          pass


#  class Nested(Interpreter):
#      """
#      Interpret a nested data structure (e.g. JSON)
#      """
#      def cast(self, nest):
#          pass


class Phrase:
    def __init__(self, tokens: List[Token], levels: Optional[Set[str]] = None):
        self.tokens: List[Token] = tokens
        self.levels: Optional[Set[str]] = levels

    def connect(self, taguri=None) -> Set[Tuple[Node, Node, Node]]:
        """
        Create links between a list of Tokens. For example, they may be related
        by fields in a fasta header or elements in a row in a table.
        """

        g = set()

        for token in self.tokens:
            if token.clean is None:
                continue

            # If no restrictions have been placed on the levels
            # or if the current token is one of the allowed levels
            # then find relations
            if self.levels is None or (token.group in self.levels):
                g.update(token.relate(tokens=self.tokens, levels=self.levels))
            g.update(token.add_triples())
            if taguri and token.group:
                turi = token.as_uri()
                if turi:
                    g.add((turi, P.tag, taguri))

        return g

    def __str__(self):
        return str([(t.typename, t.field, t.clean) for t in self.tokens])
