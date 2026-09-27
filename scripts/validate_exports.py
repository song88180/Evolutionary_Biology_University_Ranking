"""Check export consistency, not scientific completeness or final ranking validity."""
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
from fractions import Fraction
import json

from study_config import START, END, INVENTORY, ROOT


def read_csv(name):
    with (ROOT / "data" / name).open() as stream:
        return list(csv.DictReader(stream))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    pool = read_csv("arwu_2026_top1000.csv")
    pool_ids = {r["institution_id"] for r in pool}
    require(len(pool) == len(pool_ids) == 1000, "Eligibility pool must contain exactly 1,000 distinct institutions")
    papers = read_csv("papers_reviewed_INCOMPLETE.csv")
    credits = read_csv("paper_credits_INCOMPLETE.csv")
    weights = read_csv("journal_impact_factors.csv")
    require(len(weights) == 11 and {r["jif_data_year"] for r in weights} == {"2025"}, "Inconsistent JIF series")
    require(len({r["doi"] for r in papers}) == len(papers), "Duplicate reviewed DOI")
    require(len({(r["doi"], r["institution_id"]) for r in credits}) == len(credits), "Duplicate paper–institution credit")
    by_doi = defaultdict(list)
    for row in credits:
        by_doi[row["doi"]].append(row)
        require((row["eligible_arwu_top1000"] == "true") == (row["institution_id"] in pool_ids), "Eligibility flag does not match pool")
    for paper in papers:
        doi = paper["doi"]
        require(START <= paper["publication_date"] <= END, "Included date outside confirmed window: " + doi)
        require(paper["correspondence_evidence_status"] in {"explicit_publisher_links_parsed", "explicit_repository_links_parsed"}, "Non-primary correspondence evidence: " + doi)
        authors = json.loads(paper["corresponding_author_affiliations_json"])
        require(authors and all(a["name"] and a["affiliations"] for a in authors), "Missing corresponding author or linked affiliation: " + doi)
        allocations = by_doi.pop(doi, [])
        if paper["credit_status"] != "ready":
            require(not allocations, "Unresolved paper received points: " + doi)
            continue
        mappings = json.loads(paper["normalized_affiliations_json"])
        exempted = json.loads(paper.get("exempted_affiliations_json") or "[]")
        expected = {m["institution_id"] for m in mappings}
        require({a["institution_id"] for a in allocations} == expected, "Incomplete institution denominator: " + doi)
        covered = {(m["author"], m["affiliation"]) for m in mappings} | {(e["author"], e["affiliation"]) for e in exempted}
        require(covered == {(a["name"], f["address"]) for a in authors for f in a["affiliations"]}, "An affiliation has no institution mapping: " + doi)
        require(sum((Fraction(a["impact_factor_points_exact"]) for a in allocations), Fraction()) == Fraction(paper["journal_impact_factor"]), "Credits do not conserve JIF: " + doi)
        require(all(Fraction(a["fraction_exact"]) == Fraction(1, len(expected)) for a in allocations), "Unequal institution shares: " + doi)
        require(all(Fraction(a["impact_factor_points_exact"]) == Fraction(paper["journal_impact_factor"]) / len(expected) for a in allocations), "Incorrect fractional points: " + doi)
    require(not by_doi, "Credit rows reference papers outside the reviewed set")
    query_checks = []
    for path in sorted(INVENTORY.glob("*_*.json")):
        if not path.name.endswith(("_epmc.json", "_openalex.json", "_crossref.json")):
            continue
        payload = json.loads(path.read_text())
        require(len(payload["records"]) == payload["expected_hits"], "Incomplete metadata query: " + path.name)
        if "database_query_exhausted" in payload:
            require(payload["database_query_exhausted"], "Query cursor not exhausted: " + path.name)
        query_checks.append(path.name)
    require(len(query_checks) == 33, "Expected three metadata inventories for each of eleven journals")
    audit = read_csv("screening_audit_INCOMPLETE.csv")
    require({p["doi"] for p in papers} == {r["doi"] for r in audit if r["review_status"] == "included_in_reviewed_subset"}, "Discovery audit and reviewed subset disagree")
    evidence = Counter()
    dates = Counter()
    for path in (ROOT / "data/articles").glob("*.json"):
        article = json.loads(path.read_text())
        evidence[article.get("extraction_status", "missing")] += 1
        if article.get("date_evidence"):
            dates[article["date_evidence"]] += 1
    report = {
        "validated_utc": datetime.now(timezone.utc).isoformat(),
        "publication_start": START, "publication_end": END,
        "consistency_checks_passed": True,
        "scientific_completeness_certified": False,
        "final_ranking_ready": False,
        "arwu_eligible_institutions": len(pool_ids),
        "metadata_queries_count_matched": len(query_checks),
        "included_papers": len(papers),
        "included_papers_by_journal": dict(sorted(Counter(r["journal"] for r in papers).items())),
        "fully_allocated_papers": sum(p["credit_status"] == "ready" for p in papers),
        "credit_rows": len(credits),
        "outside_pool_credit_rows": sum(c["eligible_arwu_top1000"] == "false" for c in credits),
        "unresolved_affiliation_rows": len(read_csv("unresolved_affiliations.csv")),
        "screening_status_counts": dict(Counter(r["review_status"] for r in audit)),
        "primary_metadata_extraction_status_counts": dict(evidence),
        "date_evidence_counts": dict(dates),
        "limitations": "Count matching certifies retrieval of database queries, not complete publisher coverage. Credit checks certify arithmetic and mapping coverage, not independent correctness of every institutional identity or parser output."
    }
    (ROOT / "data/validation_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
