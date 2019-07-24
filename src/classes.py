import sys
import parsec
from src.classifiers.flucrew import allClassifiers
from src.token import (Token, Unknown)
from src.util import zipGen, strOrNone, log, concat, file_str
from src.nomenclature import make_tag_uri, P
import dateutil.parser as dateparser
import xlrd
import pandas as pd
import src.colors as colors
import datetime as datetime
from rdflib import Literal
from tqdm import tqdm


class Interpreter:
    def __init__(
        self,
        data,
        field_name=None,
        tag=None,
        classifiers=allClassifiers,
        
    ):
        self.tag = tag
        self.classifiers = classifiers
        self.field_name = field_name
        self.data = self.cast(data)

    def cast(self, data):
        raise NotImplementedError

    def load(self, g):
        raise NotImplementedError

    def summarize(self):
        raise NotImplementedError


class Datum(Interpreter):
    """
    Interpret a single word. This should not be used much.
    """
    def cast(self, data):
        for t in (c(data, field_name=self.field_name) for c in self.classifiers):
            if t:
                return t
        return self.default_classifier(data)

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
            token.add_triples(g)
        g.commit()

    def __str__(self):
        return str([t.clean for t in self.data])

class ParsedPhraseList(Interpreter):
    def __init__(self, filehandle, field_name=None, tag=None, classifiers=allClassifiers, default_classifier=Unknown):
        self.filehandle = filehandle
        self.tag = tag
        self.classifiers = classifiers
        self.default_classifier = default_classifier
        self.data = self.cast(self.parse(filehandle))

    def parse(self, filehandle):
        raise NotImplementedError

    def connect(self, g):
        log("Building ontology")

        if self.tag:
            taguri = make_tag_uri(self.tag)
            g.add((taguri, P.name, Literal(self.tag)))
            g.add((taguri, P.time, Literal(str(datetime.datetime.now()))))
            g.add((taguri, P.file, Literal(file_str(self.filehandle))))
        else:
            taguri = None

        for (i, phrase) in enumerate(tqdm(self.data)):
            phrase.connect(g, taguri=taguri)
            if i % 1000 == 0:
                g.commit()
        g.commit()

def tabularTyping(data):
    cols = []
    for k,v in data.items():
        hl = HomoList(v, field_name=k).data
        log(f" - '{k}':{colors.good(hl[0].typename)}")
        cols.append(hl)
    phrases = [Phrase([col[i] for col in cols]) for i in range(len(cols[0]))]
    return phrases

def headlessTabularTyping(data):
    cols = []
    for (i, xs) in enumerate(data):
        hl = HomoList(xs).data
        log(f" - 'X{i}':{colors.good(hl[0].typename)}")
        cols.append(hl)
    phrases = [Phrase([col[i] for col in cols]) for i in range(len(cols[0]))]
    return phrases

class Table(ParsedPhraseList):

    def cast(self, data):
        return tabularTyping(data)

    def parse(self, filehandle):
        """
        Make a dictionary with column name as key and list of strings as value. Currently only Excel is supported.
        """
        return self._parse_excel(filehandle)

    def _parse_excel(self, filehandle):
        try:
            log(f"Reading {file_str(filehandle)} as excel file ...")
            d = pd.read_excel(filehandle)
            # create a dictionary of List(str) with column names as keys
            return {c:[strOrNone(x) for x in d[c]] for c in d}
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
            return headlessTabularTyping(tabular_data)
        else:
            return [Phrase([Datum(x).data for x in row]) for row in data]

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
        entries = p_fasta.parse(filehandle.read())
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
    levels = []
    def __init__(self, tokens):
        self.tokens = tokens
        try:
            self.fields = {token.choose_field_name():token for token in tokens}
        except:
            print("FAILURE IN PHRASE", file=sys.stderr)
            print([type(t) for t in tokens], file=sys.stderr) 
            sys.exit(1)

    def connect(self, g, taguri=None):
        """
        Create links between a list of Tokens. For example, they may be related
        by fields in a fasta header or elements in a row in a table.
        """
        for (name, token) in self.fields.items():
            token.relate(self.fields, g)
            token.add_triples(g)
            if taguri and token.group:
                turi = token.as_uri()
                if turi:
                    g.add((turi, P.tag, taguri))


    def __str__(self):
        return str([(t.typename, t.field_name, t.clean) for t in self.tokens])
