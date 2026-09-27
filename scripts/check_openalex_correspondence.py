"""Fetch public correspondence candidates, with a publisher cross-check.

OpenAlex is a cross-check, not publisher confirmation or final credit evidence.
Priority is a lookup ordering aid, not an evolutionary-relevance decision.
"""
import argparse
from collections import Counter
import concurrent.futures
import csv
import hashlib
import json
import os
import threading
from urllib.parse import quote

import requests

from collect_inventory import CACHE, ROOT, fetch
from export_reviewed import normalized
from study_config import load_openalex_key
from collect_openalex_inventory import work_cache_path


FIELDS = ["doi", "journal", "title", "status", "openalex_id", "openalex_publication_date",
          "authorships_returned", "possible_authorship_truncation",
          "corresponding_authors_json", "source_url", "publisher_confirmation_status",
          "publisher_comparison", "publisher_corresponding_authors_json", "retry_after_seconds", "error"]
RATE_LIMITED = threading.Event()


def normalize_doi(doi):
    return doi.strip().lower().removeprefix("https://doi.org/").removeprefix("http://doi.org/")


def compare_publisher(authors, publisher):
    """Exact normalized text comparison only; never infer missing links.

    Name agreement does not validate affiliations. Even complete text agreement
    does not resolve institutional parents or certify publisher extraction.
    """
    if not publisher:
        return "not_available"
    if not authors:
        return "no_openalex_corresponding_authors"
    def by_name(items, primary=False):
        result = {}
        for author in items:
            name = normalized(author.get("name") or "")
            if not name or name in result:
                return None
            affiliations = author.get("affiliations", [])
            result[name] = {normalized(a["address"] if primary else a) for a in affiliations}
        return result
    candidate = by_name(authors)
    reference = by_name(publisher, primary=True)
    if candidate is None or reference is None:
        return "ambiguous_names_manual_review"
    if candidate.keys() != reference.keys():
        return "author_names_differ_manual_review"
    if candidate == reference and all(candidate.values()):
        return "names_and_raw_affiliations_agree"
    return "author_names_agree_affiliation_text_differs"


def parse_work(work, requested_doi):
    if normalize_doi(work.get("doi") or "") != requested_doi:
        raise ValueError("Returned DOI does not match requested DOI")
    authorships = work.get("authorships", [])
    authors = [{"name": a.get("raw_author_name") or a.get("author", {}).get("display_name"),
                "author_id": a.get("author", {}).get("id"),
                "affiliations": a.get("raw_affiliation_strings", []),
                "institutions": [i.get("display_name") for i in a.get("institutions", [])],
                "institution_records": a.get("institutions", []),
                "raw_affiliation_to_institution_links": a.get("affiliations", [])}
               for a in authorships if a.get("is_corresponding") is True]
    return {"status": "candidates_found" if authors else "no_corresponding_author_flag",
            "openalex_id": work.get("id", ""),
            "openalex_publication_date": work.get("publication_date", ""),
            "authorships_returned": len(authorships),
            "possible_authorship_truncation": str(len(authorships) >= 100).lower(),
            "corresponding_authors_json": json.dumps(authors, ensure_ascii=False)}


def check(row, publisher=None, cached_only=False):
    doi = normalize_doi(row["doi"])
    result = {"doi": doi, "journal": row.get("journal", ""), "title": row.get("title", ""),
              "corresponding_authors_json": "[]", "publisher_confirmation_status": "pending"}
    if not doi:
        return {**result, "status": "no_doi"}
    url = "https://api.openalex.org/works/https://doi.org/" + quote(doi, safe="/")
    result["source_url"] = url
    cache_key = hashlib.sha256(url.encode()).hexdigest()
    bulk_cache = work_cache_path(doi)
    cached = bulk_cache.exists() or all((CACHE / (cache_key + suffix)).exists() for suffix in (".body", ".json"))
    if not cached and (cached_only or RATE_LIMITED.is_set()):
        return {**result, "status": "not_yet_queried" if cached_only else "deferred_rate_limit"}
    try:
        # Keep credentials out of request URLs, cache metadata and CSV files.
        api_key = os.environ.get("OPENALEX_API_KEY")
        headers = {"Authorization": "Bearer " + api_key} if api_key else None
        if bulk_cache.exists():
            evidence = json.loads(bulk_cache.read_text())
            work = evidence["work"]
            result["source_url"] = evidence["source_url"]
        else:
            work = json.loads(fetch(url, headers=headers))
        result.update(parse_work(work, doi))
    except requests.HTTPError as error:
        if error.response is not None and error.response.status_code == 429:
            RATE_LIMITED.set()
            return {**result, "status": "rate_limited",
                    "retry_after_seconds": error.response.headers.get("Retry-After", ""),
                    "error": "OpenAlex returned HTTP 429; further uncached requests deferred"}
        return {**result, "status": "lookup_failed", "error": str(error)}
    except Exception as error:
        return {**result, "status": "lookup_failed", "error": str(error)}
    authors = json.loads(result["corresponding_authors_json"])
    result["publisher_comparison"] = compare_publisher(authors, publisher)
    result["publisher_corresponding_authors_json"] = json.dumps(publisher or [], ensure_ascii=False)
    return result


def save(path, rows):
    # A completed checkpoint survives interruptions; fetch responses are cached.
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda row: row["doi"]))
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=["access", "priority", "publisher"], default="access")
    parser.add_argument("--workers", type=int, default=4, choices=range(1, 5))
    parser.add_argument("--cached-only", action="store_true", help="Rebuild outputs without any network requests")
    args = parser.parse_args()
    load_openalex_key()
    RATE_LIMITED.clear()
    publisher_rows = {}
    for path in sorted((ROOT / "data/articles").glob("*.json")):
        paper = json.loads(path.read_text())
        if paper.get("extraction_status") == "explicit_publisher_links_parsed":
            publisher_rows[normalize_doi(paper["doi"])] = paper
    if args.scope == "publisher":
        records = list(publisher_rows.values())
    else:
        filename = "fulltext_access_candidates.csv" if args.scope == "access" else "screening_audit_INCOMPLETE.csv"
        with (ROOT / "data" / filename).open() as stream:
            records = list(csv.DictReader(stream))
        if args.scope == "priority":
            records = [r for r in records if r["priority_only_not_classification"] == "early_review" and r["doi"]]
    records = list({normalize_doi(r["doi"]): r for r in records}.values())
    filename = ("openalex_correspondence_candidates.csv" if args.scope == "access"
                else f"openalex_{args.scope}_correspondence_INCOMPLETE.csv")
    output = ROOT / "data" / filename
    rows = []
    print(f"Starting {args.scope}: {len(records)} distinct DOI lookups", flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(check, row, publisher_rows.get(normalize_doi(row["doi"]), {}).get("corresponding_authors"), args.cached_only)
                   for row in records]
        for future in concurrent.futures.as_completed(futures):
            rows.append(future.result())
            if len(rows) % 100 == 0:
                save(output, rows)
                print(f"{len(rows)}/{len(records)}: {dict(Counter(r['status'] for r in rows))}", flush=True)
    save(output, rows)
    summary = {"scope": args.scope, "requested": len(records), "output_rows": len(rows),
               "metadata_records_available": sum(r["status"] in ("candidates_found", "no_corresponding_author_flag") for r in rows),
               "cached_only": args.cached_only, "stopped_on_rate_limit": RATE_LIMITED.is_set(),
               "statuses": dict(Counter(row["status"] for row in rows)),
               "publisher_comparisons": dict(Counter(row.get("publisher_comparison", "not_compared") for row in rows)),
               "possible_authorship_truncation": sum(r.get("possible_authorship_truncation") == "true" for r in rows),
               "scientific_screening_complete": False, "ranking_produced": False}
    output.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
