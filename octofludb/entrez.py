import sys
import time
import os
from typing import List
from urllib.error import HTTPError
from Bio import Entrez
from tqdm import tqdm

Entrez.email = "zebulun.arendsee@usda.gov"

# code adapted from http://biopython.org/DIST/docs/tutorial/Tutorial.html#htoc122
def get_gbs(gb_ids: List[str]) -> List[dict]:
    batch_size = 1000
    count = len(gb_ids)
    for start in tqdm(range(0, count, batch_size)):
        end = min(count, start + batch_size)
        cache_filename = f".gb_{start}-{end}.xml"
        attempt = 0
        while attempt < 10:
            try:
                if not os.path.exists(cache_filename):
                    h = Entrez.efetch(
                        db="nucleotide", id=gb_ids[start:end], retmode="xml"
                    )
                    x = h.read()
                    h.close()
                    with open(cache_filename, "w") as f:
                        f.write(x)
                with open(cache_filename, "r") as f:
                    x = Entrez.read(f)
                    time.sleep(1)
                    yield x
                break
            except Exception as err:
                attempt += 1
                print(f"Received error from server {err}", file=sys.stderr)
                print(f"Attempt {str(attempt)} of 10 attempt", file=sys.stderr)
                time.sleep(15)
