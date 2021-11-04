import sys
import parsec
from octofludb.classifiers.flucrew import allClassifiers
from octofludb.token import Token, Unknown, Missing
from octofludb.util import zipGen, strOrNone, log, concat, file_str
from octofludb.nomenclature import make_tag_uri, P
import dateutil.parser as dateparser
import xlrd
import pandas as pd
import octofludb.colors as colors
import datetime as datetime
from rdflib import Literal
from tqdm import tqdm


def updateClassifiers(classifiers, include, exclude):
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
        data,
        field_name=None,
        tag=None,
        classifiers=allClassifiers,
        default_classifier=Unknown,
        include={},
        exclude={},
        levels=None,
        na_str=[None],
        log=False,
    ):
        self.tag = tag
        self.levels = levels
        self.na_str = na_str
        self.classifiers = updateClassifiers(classifiers, include, exclude)
        self.default_classifier = Unknown
        if log:
            self.log()
        self.field_name = field_name
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

    def cast(self, data):
        if data == "":
            return Missing(data, na_str=self.na_str)
        for classifier in self.classifiers:
            try:
                token = classifier(data, field_name=self.field_name, na_str=self.na_str)
            except TypeError:
                log(data)
                log(token)
                sys.exit(1)
            if token:
                return token
        return self.default_classifier(
            data, field_name=self.field_name, na_str=self.na_str
        )

    def summarize(self):
        log(f"typename: {self.data.typename}")
        log(f"field_name: {self.data.field_name}")
        log(f"value: {self.data.dirty}")
        log(f"munged: {self.data.clean}")

    def __str__(self):
        return str(self.data.clean)


def addTag(g, tag, filehandle):
    """
    Add tag info to the triple set and return the tag URI
    """
    if tag:
        taguri = make_tag_uri(tag)
        g.add((taguri, P.name, Literal(tag)))
        g.add((taguri, P.time, Literal(datetime.datetime.now())))
        g.add((taguri, P.file, Literal(file_str(filehandle))))
    else:
        taguri = None
    return taguri


class HomoList(Interpreter):
    """
    Interpret a list of items assumed to be of the same type
    """

    def cast(self, data):
        for classifier in self.classifiers:
            if classifier.goodness(data, na_str=self.na_str) > 0.8:
                c = classifier
                break
        else:
            c = self.default_classifier
        return [c(x, field_name=self.field_name, na_str=self.na_str) for x in data]

    def connect(self, g):
        addTag(g, tag=self.tag, filehandle=filehandle)
        for token in self.data:
            if token.clean is None:
                continue
            token.add_triples(g)

    def __str__(self):
        return str([t.clean for t in self.data])


class ParsedPhraseList(Interpreter):
    def __init__(
        self,
        filehandle,
        field_name=None,
        tag=None,
        classifiers=allClassifiers,
        default_classifier=Unknown,
        include={},
        exclude={},
        levels=None,
        na_str=[None],
        log=False,
    ):
        self.classifiers = updateClassifiers(classifiers, include, exclude)
        self.tag = tag
        self.levels = levels
        self.na_str = na_str
        if log:
            self.log()
        self.filehandle = filehandle
        self.default_classifier = default_classifier
        self.data = self.cast(self.parse(filehandle))

    def parse(self, filehandle):
        raise NotImplementedError

    def connect(self, g):
        log("Making triples")
        taguri = addTag(g, tag=self.tag, filehandle=self.filehandle)
        for (i, phrase) in enumerate(tqdm(self.data)):
            phrase.connect(g, taguri=taguri)


def tabularTyping(data, levels=None, na_str=[None]):
    cols = []
    if not data:
        return []
    for k, v in data.items():
        hl = HomoList(v, field_name=k, na_str=na_str).data
        if len(hl) > 0:
            log(f" - '{k}':{colors.good(hl[0].typename)}")
        else:
            log(f"{colors.bad('Warning:')} no data")
        cols.append(hl)
    phrases = [
        Phrase([col[i] for col in cols], levels=levels) for i in range(len(cols[0]))
    ]
    return phrases


def headlessTabularTyping(data, levels=None, na_str=[None]):
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

    def cast(self, data):
        return tabularTyping(data, levels=self.levels, na_str=self.na_str)

    def parse(self, filehandle):
        """
        Make a dictionary with column name as key and list of strings as value.
        Currently only Excel is supported.
        """
        try:
            data = self._parse_excel(filehandle)
        except:
            data = self._parse_table(filehandle)
        return data

    def _parse_excel(self, filehandle):
        try:
            log(f"Reading {file_str(filehandle)} as excel file ...")
            d = pd.read_excel(filehandle.name)
            self.header = list(d.columns)
            # create a dictionary of List(str) with column names as keys
            return {c: [strOrNone(x) for x in d[c]] for c in d}
        except xlrd.biffh.XLRDError as e:
            log(f"Could not parse '{file_str(filehandle)}' as an excel file")
            raise e
        return d

    def _parse_table(self, filehandle, delimiter="\t"):
        log(f"Reading {file_str(filehandle)} as tab-delimited file ...")
        rows = [r.split(delimiter) for r in filehandle.readlines()]
        if len(rows) < 2:
            # if the input table is empty or has only a header
            return dict()
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

    def cast(self, data):
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

    def parse(self, filehandle):
        """
        Return a list of lists of strings. Currently only FASTA is supported.
        """
        return self._parse_fasta(filehandle, sep="|")

    def _parse_fasta(self, filehandle, sep="|"):
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
        log(f"Reading {file_str(filehandle)} as a fasta file:")
        try:
            entries = p_fasta.parse(filehandle.read())
        except AttributeError:
            # in case I want to pass in a list of strings, e.g., in tests
            entries = p_fasta.parse(filehandle)
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
    def __init__(self, tokens, levels=None):
        self.tokens = tokens
        self.levels = levels

    def connect(self, g, taguri=None):
        """
        Create links between a list of Tokens. For example, they may be related
        by fields in a fasta header or elements in a row in a table.
        """
        for token in self.tokens:
            if token.clean is None:
                continue
            if (self.levels is None) or (token.group in self.levels):
                token.relate(self.tokens, g, levels=self.levels)
            token.add_triples(g)
            if taguri and token.group:
                turi = token.as_uri()
                if turi:
                    g.add((turi, P.tag, taguri))

    def __str__(self):
        return str([(t.typename, t.field_name, t.clean) for t in self.tokens])
