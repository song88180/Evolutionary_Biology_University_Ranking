"""Retrieve publisher-deposited online publication dates and journal inventory."""
import argparse
import concurrent.futures
import json
import time
from urllib.parse import urlencode

from collect_inventory import JOURNALS, fetch
from study_config import END, INVENTORY, START


def iso_date(value):
    parts = (value or {}).get("date-parts", [[]])[0]
    return f"{parts[0]:04d}-{parts[1]:02d}-{parts[2]:02d}" if len(parts) == 3 else ""


def collect(slug):
    journal, issn = JOURNALS[slug]
    records, pages, errors = {}, [], []
    cursor = "*"
    expected = None
    exhausted = False
    try:
        while True:
            url = f"https://api.crossref.org/journals/{issn}/works?" + urlencode({
                "filter": f"from-online-pub-date:{START},until-online-pub-date:{END}",
                "rows": 1000, "cursor": cursor,
                "select": "DOI,title,published-online,published-print,type,URL,ISSN"})
            payload = json.loads(fetch(url))["message"]
            expected = payload["total-results"]
            batch = payload.get("items", [])
            pages.append(url)
            for record in batch:
                records[record["DOI"].lower()] = {**record, "source_url": url}
            print(f"{slug}: Crossref {len(records)}/{expected}", flush=True)
            if len(batch) < 1000 or len(records) >= expected:
                exhausted = True
                break
            following = payload.get("next-cursor")
            if not following or following == cursor:
                raise ValueError("Crossref cursor failed to advance")
            cursor = following
            time.sleep(1)
    except Exception as error:
        errors.append(str(error))
        print(f"{slug}: Crossref stopped: {error}", flush=True)
    result = {"journal": journal, "start": START, "end": END, "expected_hits": expected,
              "records": list(records.values()), "page_urls": pages, "errors": errors,
              "database_query_exhausted": exhausted, "publisher_completeness_verified": False}
    INVENTORY.mkdir(parents=True, exist_ok=True)
    (INVENTORY / f"{slug}_crossref.json").write_text(json.dumps(result, ensure_ascii=False) + "\n")
    return {k: result[k] for k in ("journal", "expected_hits", "errors", "database_query_exhausted")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("journals", nargs="+", choices=JOURNALS)
    args = parser.parse_args()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        print(json.dumps(list(executor.map(collect, args.journals))), flush=True)
