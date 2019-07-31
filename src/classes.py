import sys
import parsec
from src.classifiers.flucrew import allClassifiers
from src.token import Token, Unknown, Missing
from src.util import zipGen, strOrNone, log, concat, file_str
from src.nomenclature import make_tag_uri, P
import dateutil.parser as dateparser
import xlrd
import pandas as pd
import src.colors as colors
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
        log=False,
    ):
        self.tag = tag
        self.levels = levels
        self.classifiers = updateClassifiers(classifiers, include, exclude)
        self.default_classifier=Unknown,
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
            return Missing(data)
        for classifer in self.classifiers:
            try:
                token = classifer(data, field_name=self.field_name)
            except TypeError:
                log(data)
                log(token)
                sys.exit(1)
            if token:
                return token
        return self.default_classifier(data, field_name=self.field_name)

    def summarize(self):
        log(f"typename: {self.data.typename}")
        log(f"field_name: {self.data.field_name}")
        log(f"value: {self.data.dirty}")
        log(f"munged: {self.data.clean}")

    def __str__(self):
        return str(self.data.clean)


class HomoList(Interpreter):
    """
    Interpret a list of items assumed to be of the same type
    """

    def cast(self, data):
        for classifier in self.classifiers:
            if classifier.goodness(data) > 0.8:
                c = classifier
                break
        else:
            c = self.default_classifier
        return [c(x, field_name=self.field_name) for x in data]

    def connect(self, g):
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
        log=False,
    ):
        self.classifiers = updateClassifiers(classifiers, include, exclude)
        self.tag = tag
        self.levels = levels
        if log:
            self.log()
        self.filehandle = filehandle
        self.default_classifier = default_classifier
        self.data = self.cast(self.parse(filehandle))

    def parse(self, filehandle):
        raise NotImplementedError

    def connect(self, g):
        log("Building ontology")

        if self.tag:
            taguri = make_tag_uri(self.tag)
            g.add((taguri, P.name, Literal(self.tag)))
            g.add((taguri, P.time, Literal(datetime.datetime.now())))
            g.add((taguri, P.file, Literal(file_str(self.filehandle))))
        else:
            taguri = None

        for (i, phrase) in enumerate(tqdm(self.data)):
            phrase.connect(g, taguri=taguri)


def tabularTyping(data, levels=None):
    cols = []
    for k, v in data.items():
        hl = HomoList(v, field_name=k).data
        log(f" - '{k}':{colors.good(hl[0].typename)}")
        cols.append(hl)
    phrases = [Phrase([col[i] for col in cols], levels=levels) for i in range(len(cols[0]))]
    return phrases


def headlessTabularTyping(data, levels=None):
    cols = []
    for (i, xs) in enumerate(data):
        hl = HomoList(xs).data
        log(f" - 'X{i}':{colors.good(hl[0].typename)}")
        cols.append(hl)
    phrases = [Phrase([col[i] for col in cols], levels=levels) for i in range(len(cols[0]))]
    return phrases


class Column:
    def __init__(self, field_name, classifier=Unknown, extractWith=None):
        self.classifier = classifier
        self.field_name = field_name
        self.unwrap = lambda x: x
        if extractWith:

            def unwrap(self, x):
                try:
                    match = re.search(extractWith, x).group(0)
                except AttributeError:
                    match = ""
                return match

    def cast(self, xs):
        return [self.classifier(self.unwrap(x), field_name=field_name) for x in xs]


class Table(ParsedPhraseList):
    def __init__(self, headers=[], **kwargs):
        self.headers = headers
        super().__init__(**kwargs)

    def cast(self, data):
        if self.headers:
            if len(self.headers) != len(data):
                log(
                    "The number of described columns doesn't equal the number of observed columns"
                )
                exit(1)
            else:
                cols = [c.cast(d) for c, d in zip(headers, data)]
                result = [Phrase([col[i] for col in cols], levels=self.levels) for i in range(len(cols[0]))]
        else:
            result = tabularTyping(data, levels=self.levels)
        return result

    def parse(self, filehandle):
        """
        Make a dictionary with column name as key and list of strings as value. Currently only Excel is supported.
        """
        return self._parse_excel(filehandle)

    def _parse_excel(self, filehandle):
        try:
            log(f"Reading {file_str(filehandle)} as excel file ...")
            d = pd.read_excel(filehandle.name)
            # create a dictionary of List(str) with column names as keys
            return {c: [strOrNone(x) for x in d[c]] for c in d}
        except xlrd.biffh.XLRDError as e:
            log(f"Could not parse '{file_str(filehandle)}' as an excel file")
            sys.exit(1)
        return d


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
            return headlessTabularTyping(tabular_data, levels=self.levels)
        else:
            return [Phrase([Datum(x).data for x in row], levels=self.levels) for row in data]

    def parse(self, filehandle):
        """
        Return a list of lists of strings. Currently only FASTA is supported. 
        """
        return self._parse_fasta(filehandle, sep="|")

    def _parse_fasta(self, filehandle, sep="|"):
        """
        Parse a fasta file. The header is split into fields on 'sep'. The sequence is added as a final field.
        """
        p_header = parsec.string(">") >> parsec.regex(".*") << parsec.spaces()
        p_seq = (
            parsec.sepBy1(
                parsec.regex("[^>\n]*"), sep=parsec.regex("[\r\n\t ]+")
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
