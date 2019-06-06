import sys
import time
from Bio import Entrez
from typing import List
from urllib.error import HTTPError

Entrez.email = "zebulun.arendsee@usda.gov"

# code adapted from http://biopython.org/DIST/docs/tutorial/Tutorial.html#htoc122
def get_gbs(gb_ids:List[str])->List[dict]:
  batch_size = 1000
  count = len(gb_ids)
  for start in range(0, count, batch_size):
    end = min(count-1, start+batch_size)
    attempt = 0;
    while attempt < 10:
      try:
        h = Entrez.efetch(db="nucleotide", id=gb_ids[start:end], retmode="xml")
        print(f'Downloaded Genbank entries {start+1}-{end}', file=sys.stderr)
        x = Entrez.read(h)
        h.close()
        time.sleep(1)
        yield x
        break
      except HTTPError as err:
        if 500 <= err.code <= 599:
            attempt += 1
            print(f'Received error from server {err}', file=sys.stderr)
            print(f'Attempt {attempt} of 10 attempt', file=sys.stderr)
            time.sleep(15)
        else:
            raise
