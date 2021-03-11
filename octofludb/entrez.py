import sys
import time
import os
import requests
import datetime
from typing import List
from urllib.error import HTTPError
from Bio import Entrez
from tqdm import tqdm
from octofludb.util import log
import octofludb.colors as colors
import pgraphdb as db

Entrez.email = "zebulun.arendsee@usda.gov"


def get_all_acc_in_db(url="http://localhost:7200", repo="octofludb"):

    sparql_filename = os.path.join(os.path.dirname(__file__), "data", "all-acc.rq")

    acc = db.sparql_query(sparql_file=sparql_filename, url=url, repo_name=repo)

    return [x["acc"]["value"] for x in acc["results"]["bindings"]]


def get_acc_by_date(
    mindate, maxdate, ignore=[], retmax=100000, query='"Influenza+A+Virus"[Organism]'
):
    """
    mindate: a date string of form YYYY/MM, e.g. "2020/01"
    maxdate: a date string of form YYYY/MM, e.g. "2020/06"
    """
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "nuccore",
        "term": query,
        "retmode": "json",
        "retmax": str(retmax),
        "datetype": "pdat",
        "mindate": mindate,
        "maxdate": maxdate,
        "idtype": "acc",
    }

    req = requests.get(base, params=params)
    try:
        result = req.json()["esearchresult"]

        if int(result["retmax"]) < int(result["count"]):
            log(
                f'{colors.bad("Warning:")} results truncated at {result["retmax"]} of {result["count"]} ids'
            )
    except:
        log(f'{colors.bad("Error:")} could not find "esearchresult"')
        log(str(req))
        log(params)
        return []

    # For great manner
    time.sleep(1)

    return result["idlist"]


def missing_acc_by_date(
    min_year=1918,
    max_year=2099,
    nmonths=9999,
    url="http://localhost:7200",
    repo="octofludb",
):
    """
    Find all genbank accessions that are missing from the database. Return as a tuples of (date, [accession])
    """
    now = datetime.datetime.now()
    cur_year, cur_month = now.year, now.month

    old_acc = {s for s in get_all_acc_in_db(url=url, repo=repo)}

    # step backwards in time, month-by-month to year 2000
    for year in reversed(range(2000, cur_year + 1)):
        if year < min_year:
            break
        if year > max_year:
            continue
        for month in reversed(range(1, 12 + 1)):
            if nmonths <= 0:
                break

            if year == cur_year and month > cur_month:
                # pulling future sequences is not yet supported
                continue
            mth_acc = get_acc_by_date(
                mindate=f"{str(year)}/{str(month)}", maxdate=f"{str(year)}/{str(month)}"
            )
            new_acc = [acc for acc in mth_acc if not acc in old_acc]
            nmonths -= 1
            yield (f"{str(year)}/{str(month)}", new_acc)

    # step backwards in time, year-by-year to year 1918
    for year in reversed(range(1918, 2000)):
        if year < min_year or nmonths <= 0:
            break
        if year > max_year:
            continue
        year_acc = get_acc_by_date(mindate=str(year), maxdate=str(year))
        new_acc = [acc for acc in year_acc if not acc in old_acc]
        #  nmonths -= 12
        yield (str(year), new_acc)


# code adapted from http://biopython.org/DIST/docs/tutorial/Tutorial.html#htoc122
def get_gbs(gb_ids: List[str]) -> List[dict]:
    batch_size = 1000
    count = len(gb_ids)
    for start in tqdm(range(0, count, batch_size)):
        end = min(count, start + batch_size)
        attempt = 0
        while attempt < 10:
            try:
                h = Entrez.efetch(db="nucleotide", id=gb_ids[start:end], retmode="xml")
                x = Entrez.read(h)
                h.close()
                yield x
                break
            except Exception as err:
                attempt += 1
                print(f"Received error from server {err}", file=sys.stderr)
                print(f"Attempt {str(attempt)} of 10 attempt", file=sys.stderr)
                time.sleep(15)
