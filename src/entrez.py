from Bio import Entrez
from typing import List
import json

Entrez.email = "zebulun.arendsee@usda.gov"

def get_gbs(gb_ids:List[str])->dict:
  h = Entrez.efetch(db="nucleotide", id=gb_ids, retmode="xml")
  return(Entrez.read(h))
