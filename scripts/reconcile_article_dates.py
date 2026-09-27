"""Resolve untyped repository dates using publisher-deposited online dates."""
from collections import Counter
import csv
import json

from collect_crossref_inventory import iso_date
from study_config import END, INVENTORY, ROOT, START


def main():
    deposits = {}
    for path in INVENTORY.glob("*_crossref.json"):
        for record in json.loads(path.read_text())["records"]:
            deposits[record["DOI"].lower()] = record
    supplemental = ROOT / "data/crossref_date_evidence.json"
    if supplemental.exists():
        for result in json.loads(supplemental.read_text()):
            if "record" in result:
                deposits[result["doi"]] = result["record"]
    results = []
    for path in sorted((ROOT / "data/articles").glob("*.json")):
        article = json.loads(path.read_text())
        record = deposits.get(article.get("doi", "").lower())
        if not record:
            continue
        date = iso_date(record.get("published-online"))
        if not date:
            continue
        previous = article.get("publisher_date", "")
        status = "agrees" if previous == date else "date_conflict" if previous else "date_supplied_by_publisher_deposit"
        results.append({"doi": article["doi"], "article_evidence_date": previous,
                        "crossref_online_date": date, "comparison": status,
                        "source_url": record["source_url"]})
        article["crossref_online_date"] = date
        article["date_comparison"] = status
        article["crossref_date_source_url"] = record["source_url"]
        if article.get("extraction_status") == "repository_links_need_review" and not previous and not article.get("unlinked_correspondence_notes"):
            article["publisher_date"] = date
            article["date_evidence"] = "publisher_deposited_online_date_via_crossref"
            article["extraction_status"] = "explicit_repository_links_parsed"
        path.write_text(json.dumps(article, ensure_ascii=False, indent=2) + "\n")
    output = ROOT / "data/publication_date_audit.csv"
    with output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["doi", "article_evidence_date", "crossref_online_date", "comparison", "source_url"])
        writer.writeheader()
        writer.writerows(results)
    print(dict(Counter(r["comparison"] for r in results)))


if __name__ == "__main__":
    main()
