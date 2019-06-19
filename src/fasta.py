from src.parser import (p_dnaseq, p_proseq, guess_fields, resolve)
from src.util import (concat)
import parsec as p


def parse_fasta(filename):
  p_header = p.string(">") >> p.regex(".*") << p.spaces()
  p_seq = p.sepBy1(p.regex("[^>\n]*"), sep=p.regex("[\r\n\t ]+")).parsecmap(concat) << p.spaces()
  p_entry = p_header + p_seq
  p_fasta = p.many1(p_entry)

  with open(filename, "r") as f:
    fields = (h.split(sep) + [q] for (h,q) in p_fasta.parse(f.read()))
    return resolve(guess_fields(fields))

def write_fasta(fields, filename):
  with open(filename+"~", "w") as f:
    for entry in fields:
      header = '|'.join((f'{str(entry[i][0])}={str(entry[i][1])}' for i in range(len(entry)-1)))
      seq = entry[-1][1]
      print(">" + header, file=f)
      print(seq, file=f)
