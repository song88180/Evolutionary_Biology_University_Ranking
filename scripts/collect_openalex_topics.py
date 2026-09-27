"""Add topic metadata for organizing review, never for automatic inclusion.

Uses the same journal/date query as discovery and preserves the original works.
Topic assignment is machine-generated and is not evidence of eligibility.
"""
import argparse
import concurrent.futures
import json
from urllib.parse import urlencode

from collect_inventory import JOURNALS, fetch
from study_config import START, END, INVENTORY, openalex_headers, load_openalex_key


def collect(slug):
    cursor, records, pages = "*", {}, []
    expected, exhausted, errors = None, False, []
    try:
        while True:
            url = "https://api.openalex.org/works?" + urlencode({
                "filter": f"primary_location.source.issn:{JOURNALS[slug][1]},from_publication_date:{START},to_publication_date:{END}",
                "per_page": 200, "cursor": cursor,
                "select": "id,doi,title,primary_topic,topics,keywords"})
            payload = json.loads(fetch(url, headers=openalex_headers()))
            expected = payload["meta"]["count"]
            pages.append(url)
            batch = payload.get("results", [])
            records.update({r["id"]: r for r in batch})
            following = payload["meta"].get("next_cursor")
            if not batch or not following:
                exhausted = True
                break
            if cursor == following:
                raise ValueError("Repeated cursor")
            cursor = following
            if len(records) % 1000 == 0:
                print(f"{slug}: topics {len(records)}/{expected}", flush=True)
    except Exception as error:
        errors.append(str(error))
    result = {"journal": JOURNALS[slug][0], "expected_hits": expected,
              "records": list(records.values()), "page_urls": pages,
              "database_query_exhausted": exhausted, "errors": errors,
              "role": "Machine-generated topic metadata for review organization, not eligibility evidence"}
    (INVENTORY / f"{slug}_openalex_topics.json").write_text(json.dumps(result, ensure_ascii=False) + "\n")
    return {"journal": JOURNALS[slug][0], "records": len(records), "expected": expected, "exhausted": exhausted, "errors": errors}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("journals", nargs="+", choices=JOURNALS)
    args = parser.parse_args()
    if not load_openalex_key():
        raise SystemExit("OpenAlex API key is required")
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        for summary in executor.map(collect, args.journals):
            print(json.dumps(summary), flush=True)
