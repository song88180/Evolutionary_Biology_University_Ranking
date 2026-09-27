"""Collect complete OpenAlex journal queries, retaining correspondence evidence.

An exhausted database query is not proof of exhaustive publisher coverage.
"""
import argparse
import concurrent.futures
import hashlib
import json
from urllib.parse import urlencode

from collect_inventory import JOURNALS, fetch
from study_config import END, INVENTORY, ROOT, START, load_openalex_key, openalex_headers

WORK_CACHE = ROOT / "data/openalex_works"


def work_cache_path(doi):
    return WORK_CACHE / (hashlib.sha256(doi.lower().encode()).hexdigest() + ".json")


def collect(slug):
    journal, issn = JOURNALS[slug]
    cursor = "*"
    records = {}
    pages = []
    errors = []
    expected = None
    exhausted = False
    INVENTORY.mkdir(parents=True, exist_ok=True)
    WORK_CACHE.mkdir(parents=True, exist_ok=True)
    fields = "id,doi,title,publication_date,type,authorships,corresponding_author_ids,corresponding_institution_ids,primary_location,locations,abstract_inverted_index,language,is_retracted"
    try:
        while True:
            query = {"filter": f"primary_location.source.issn:{issn},from_publication_date:{START},to_publication_date:{END}",
                     "per_page": 100, "cursor": cursor, "select": fields}
            url = "https://api.openalex.org/works?" + urlencode(query)
            payload = json.loads(fetch(url, headers=openalex_headers()))
            expected = payload["meta"]["count"]
            batch = payload.get("results", [])
            pages.append(url)
            for work in batch:
                records[work["id"]] = work
                doi = (work.get("doi") or "").removeprefix("https://doi.org/").lower()
                if doi:
                    work_cache_path(doi).write_text(json.dumps({"work": work, "source_url": url}, ensure_ascii=False) + "\n")
            print(f"{slug}: OpenAlex {len(records)}/{expected}", flush=True)
            following = payload.get("meta", {}).get("next_cursor")
            if not batch or not following:
                exhausted = True
                break
            if following == cursor:
                raise ValueError("OpenAlex cursor repeated before exhaustion")
            cursor = following
    except Exception as error:
        errors.append(str(error))
        print(f"{slug}: OpenAlex stopped: {error}", flush=True)
    result = {"journal": journal, "start": START, "end": END, "expected_hits": expected,
              "records": list(records.values()), "page_urls": pages,
              "database_query_exhausted": exhausted, "errors": errors,
              "publisher_completeness_verified": False}
    (INVENTORY / f"{slug}_openalex.json").write_text(json.dumps(result, ensure_ascii=False) + "\n")
    return {"journal": journal, "records": len(records), "expected_hits": expected,
            "database_query_exhausted": exhausted, "errors": errors}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("journals", nargs="+", choices=JOURNALS)
    parser.add_argument("--workers", type=int, default=3, choices=range(1, 5))
    args = parser.parse_args()
    if not load_openalex_key():
        raise SystemExit("An OpenAlex key is required for this bulk collection")
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        summaries = list(executor.map(collect, args.journals))
    (INVENTORY / "openalex_collection_status.json").write_text(json.dumps(summaries, indent=2) + "\n")
    print(json.dumps(summaries), flush=True)
