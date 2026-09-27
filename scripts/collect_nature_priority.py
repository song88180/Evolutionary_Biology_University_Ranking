"""Fetch primary article evidence for a bounded, resumable Nature review queue.

Priority is a discovery aid, not an inclusion decision. Existing explicit
evidence is preserved. Each fetched page must identify its DOI and research type.
"""
import argparse
from collections import Counter
import concurrent.futures
import csv
import json

from collect_inventory import ROOT
from collect_nature_articles import article
from study_config import screening_decisions


def collect(row):
    target = ROOT / "data/articles" / (row["doi"].split("/")[-1] + ".json")
    try:
        result = article({**row, "article_url": "https://www.nature.com/articles/" + row["doi"].split("/")[-1]})
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        return {"doi": row["doi"], "status": result["extraction_status"]}
    except Exception as error:
        return {"doi": row["doi"], "status": "failed", "error": str(error)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", required=True)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--all-records", action="store_true", help="Do not restrict to the keyword-priority queue")
    parser.add_argument("--review-candidates", action="store_true", help="Fetch only individually screened inclusion or unresolved relevance candidates")
    args = parser.parse_args()
    decisions = screening_decisions() if args.review_candidates else {}
    rows = []
    for row in csv.DictReader((ROOT / "data/screening_audit_INCOMPLETE.csv").open()):
        if args.review_candidates and decisions.get(row['record_id'], {}).get('decision') not in {'include_pending_primary_evidence', 'needs_abstract_review', 'needs_fuller_relevance_review'}:
            continue
        if row["journal"] != args.journal or not row["doi"].startswith("10.1038/") or (not args.all_records and row["priority_only_not_classification"] != "early_review") or row["review_status"].startswith("excluded"):
            continue
        target = ROOT / "data/articles" / (row["doi"].split("/")[-1] + ".json")
        if target.exists() and json.loads(target.read_text()).get("extraction_status") in ("explicit_publisher_links_parsed", "explicit_repository_links_parsed", "publisher_type_metadata_parsed"):
            continue
        rows.append(row)
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        for result in executor.map(collect, rows[:args.limit]):
            results.append(result)
            if len(results) % 20 == 0:
                print(f"{args.journal}: {len(results)}/{min(len(rows), args.limit)} {dict(Counter(r['status'] for r in results))}", flush=True)
    path = ROOT / "data/nature_priority_collection_status.json"
    previous = {r["doi"]: r for r in json.loads(path.read_text())} if path.exists() else {}
    previous.update({r["doi"]: r for r in results})
    path.write_text(json.dumps(list(previous.values()), indent=2) + "\n")
    print(json.dumps({"journal": args.journal, "attempted": len(results), "remaining_queue": max(0, len(rows) - len(results)), "statuses": dict(Counter(r['status'] for r in results))}), flush=True)


if __name__ == "__main__":
    main()
