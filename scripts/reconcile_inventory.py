"""Build a DOI-level audit queue; this does not certify source completeness."""
import csv
import json
from pathlib import Path
import re
import html
from collections import defaultdict

from collect_inventory import ROOT, JOURNALS
from study_config import START, END, INVENTORY, screening_decisions
from collect_crossref_inventory import iso_date

PRIORITY = re.compile(r"evolut|phylogen|speciation|natural selection|sexual selection|paleogen|palaeogen|ancient DNA|population genetic|adaptation|coevol|co-evol|domestication", re.I)


def abstract_text(index):
    if not index:
        return ""
    return " ".join(word for _, word in sorted((position, word) for word, positions in index.items() for position in positions))


def normalized_title(value):
    # Decode escaped markup before removing tags, including doubly escaped
    # italics in database titles; otherwise a missing-DOI alias can look unique.
    for _ in range(3):
        decoded = html.unescape(value)
        if decoded == value:
            break
        value = decoded
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"[^\w]+", "", value.casefold())


def empty_record(key, doi, journal, title):
    return {"record_id": key, "doi": doi, "journal": journal, "title": title,
            "database_first_publication_date": "", "publisher_publication_date": "",
            "publisher_article_type": "", "database_publication_types": "", "pmid": "", "pmcid": "",
            "publisher_url": "", "seen_in_publisher_inventory": "false", "seen_in_openalex": "false",
            "openalex_publication_date": "", "openalex_type": "", "crossref_online_date": "",
            "seen_in_crossref_online_query": "false", "document_type_assessment": "unreviewed",
            "review_status": "unreviewed", "credit_status": "not_assessed",
            "relevance_review_reason": "", "relevance_review_evidence": "",
            "canonical_article_doi": "",
            "priority_only_not_classification": "ordinary"}


def main():
    inventory = INVENTORY
    records = {}
    counts = []
    for slug, (journal, _) in JOURNALS.items():
        path = inventory / f"{slug}_epmc.json"
        payload = json.loads(path.read_text())
        counts.append({"journal": journal, "publication_start": START, "publication_end": END,
                       "database_records": len(payload["records"]),
                       "database_query_hits": payload["expected_hits"],
                       "openalex_records": 0, "openalex_query_hits": 0, "openalex_query_exhausted": "false",
                       "crossref_online_records": 0, "crossref_online_query_hits": 0,
                       "publisher_inventory_reconciled": "false", "full_article_audit_complete": "false"})
        for paper in payload["records"]:
            doi = paper.get("doi", "").strip().lower()
            key = doi or f'{paper.get("source")}:{paper["id"]}'
            record = records.setdefault(key, empty_record(key, doi, journal, paper.get("title", "")))
            record.update({"database_first_publication_date": paper.get("firstPublicationDate", ""),
                           "database_publication_types": " | ".join(paper.get("pubTypeList", {}).get("pubType", [])),
                           "pmid": paper["id"] if paper.get("source") == "MED" else "",
                           "pmcid": paper.get("pmcid", "")})
            text = paper.get("title", "") + " " + paper.get("abstractText", "")
            if slug == "mbe" or PRIORITY.search(text):
                record["priority_only_not_classification"] = "early_review"
        oa_path = inventory / f"{slug}_openalex.json"
        if oa_path.exists():
            oa = json.loads(oa_path.read_text())
            counts[-1].update({"openalex_records": len(oa["records"]), "openalex_query_hits": oa["expected_hits"],
                               "openalex_query_exhausted": str(oa["database_query_exhausted"]).lower()})
            for work in oa["records"]:
                doi = (work.get("doi") or "").removeprefix("https://doi.org/").lower()
                key = doi or work["id"]
                record = records.setdefault(key, empty_record(key, doi, journal, work.get("title") or ""))
                record.update({"seen_in_openalex": "true", "openalex_publication_date": work.get("publication_date", ""),
                               "openalex_type": work.get("type", "")})
                if slug == "mbe" or PRIORITY.search((work.get("title") or "") + " " + abstract_text(work.get("abstract_inverted_index"))):
                    record["priority_only_not_classification"] = "early_review"
        # Later topic queries can discover newly indexed records. Keep them in
        # the screening universe without treating machine topics as eligibility
        # evidence or overwriting the richer original metadata snapshot.
        topic_path = inventory / f"{slug}_openalex_topics.json"
        if topic_path.exists():
            topics = json.loads(topic_path.read_text())
            for work in topics["records"]:
                doi = (work.get("doi") or "").removeprefix("https://doi.org/").lower()
                key = doi or work["id"]
                record = records.setdefault(key, empty_record(key, doi, journal, work.get("title") or ""))
                record["seen_in_openalex"] = "true"
                if slug == "mbe" or PRIORITY.search(work.get("title") or ""):
                    record["priority_only_not_classification"] = "early_review"
        crossref_path = inventory / f"{slug}_crossref.json"
        if crossref_path.exists():
            crossref = json.loads(crossref_path.read_text())
            counts[-1].update({"crossref_online_records": len(crossref["records"]), "crossref_online_query_hits": crossref["expected_hits"]})
            for item in crossref["records"]:
                doi = item["DOI"].lower()
                record = records.setdefault(doi, empty_record(doi, doi, journal, " ".join(item.get("title", []))))
                record.update({"crossref_online_date": iso_date(item.get("published-online")), "seen_in_crossref_online_query": "true"})
                if slug == "mbe" or PRIORITY.search(record["title"]):
                    record["priority_only_not_classification"] = "early_review"
    publisher_paths = sorted((ROOT / "data/inventory").glob("*_publisher.csv")) + sorted(inventory.glob("*_publisher.csv"))
    for path in publisher_paths:
        for paper in csv.DictReader(path.open()):
            if not START <= paper["publication_date"] <= END:
                continue
            key = paper["doi"].lower()
            record = records.setdefault(key, empty_record(key, key, paper["journal"], paper["title"]))
            record.update({"publisher_publication_date": paper["publication_date"],
                           "publisher_article_type": paper["article_type"], "publisher_url": paper["article_url"],
                           "seen_in_publisher_inventory": "true"})
            if PRIORITY.search(paper["title"] + " " + paper.get("publisher_summary", "")):
                record["priority_only_not_classification"] = "early_review"
    # Exact unique title matches only; preserve alias rows and their provenance.
    # Repository DOI copies and missing-DOI PMC records must not count twice.
    def title_key(row):
        return row["journal"], normalized_title(row["title"])
    canonical_titles = defaultdict(list)
    prefixes = {"Nature": "10.1038/", "Nature Communications": "10.1038/",
                "Nature Ecology & Evolution": "10.1038/", "Nature Genetics": "10.1038/",
                "Nature Human Behaviour": "10.1038/", "Science": "10.1126/science.",
                "Science Advances": "10.1126/sciadv.", "Cell": "10.1016/j.cell.",
                "Current Biology": "10.1016/j.cub.", "Proceedings of the National Academy of Sciences": "10.1073/pnas.",
                "Molecular Biology and Evolution": "10.1093/molbev/"}
    for record in records.values():
        if record["doi"].startswith(prefixes[record["journal"]]):
            canonical_titles[title_key(record)].append(record["doi"])
    for record in records.values():
        if record["doi"].startswith(prefixes[record["journal"]]):
            continue
        matches = canonical_titles.get(title_key(record), [])
        if len(matches) == 1:
            record["canonical_article_doi"] = matches[0]
            canonical = records[matches[0]]
            for field in ["pmcid", "pmid", "database_publication_types", "database_first_publication_date"]:
                if not canonical[field] and record[field]:
                    canonical[field] = record[field]
    identifier_overrides = ROOT / "data/identifier_overrides.json"
    if identifier_overrides.exists():
        for doi, override in json.loads(identifier_overrides.read_text()).items():
            if doi in records:
                if records[doi]["pmcid"] and records[doi]["pmcid"] != override["pmcid"]:
                    raise ValueError("Conflicting PMC identifier for " + doi)
                records[doi]["pmcid"] = override["pmcid"]
    for path in (ROOT / "data/articles").glob("*.json"):
        paper = json.loads(path.read_text())
        if paper.get("extraction_status") not in {"explicit_publisher_links_parsed", "publisher_type_metadata_parsed", "explicit_repository_links_parsed"} or paper.get("doi") not in records:
            continue
        records[paper["doi"]].update({"publisher_article_type": paper.get("article_type", ""),
                                     "publisher_publication_date": paper.get("publisher_date", ""),
                                     "publisher_url": paper.get("article_url", "")})
    research_types = {"Article", "Letter", "Brief Communication", "Analysis", "Technical Report", "Resource", "Matters Arising", "Registered Report", "research-article", "brief-report"}
    excluded_types = {"Review", "Review Article", "Perspective", "Comment", "Editorial", "News", "News & Views", "Research Highlight", "Research Briefing", "Author Correction", "Publisher Correction", "Correction", "Retraction Note", "Books & Arts", "Book Review", "World View", "Q&A", "Correspondence", "Obituary", "Species Spotlight"}
    excluded_types.update({"Year in Review", "Research Highlights", "Editorial Expression of Concern", "Matters Arising Reply", "review-article", "editorial", "correction", "article-commentary", "in-brief", "reply"})
    excluded_database_types = {"Review", "review-article", "Published Erratum", "correction", "Editorial", "editorial", "News", "Comment", "article-commentary", "Retraction Notice", "Retraction of Publication", "In Brief", "in-brief", "reply"}
    for record in records.values():
        publisher_type = record["publisher_article_type"]
        database_types = set(record["database_publication_types"].split(" | "))
        if record["canonical_article_doi"]:
            record.update({"review_status": "duplicate_source_record", "credit_status": "not_eligible"})
        elif record["publisher_publication_date"] and not START <= record["publisher_publication_date"] <= END:
            record.update({"review_status": "excluded_publisher_date_outside_window", "credit_status": "not_eligible"})
        elif publisher_type in research_types:
            record["document_type_assessment"] = "publisher_research_type_requires_relevance_review"
        elif publisher_type in excluded_types:
            record.update({"review_status": "excluded_nonoriginal_publisher_type", "credit_status": "not_eligible", "document_type_assessment": "excluded_by_publisher_type"})
        elif database_types & excluded_database_types:
            record.update({"review_status": "excluded_nonoriginal_database_type", "credit_status": "not_eligible", "document_type_assessment": "excluded_by_database_type_pending_publisher_reconciliation"})
        elif record["openalex_type"] in {"dataset", "software", "dissertation", "book", "book-chapter"}:
            record.update({"review_status": "excluded_nonarticle_research_object", "credit_status": "not_eligible", "document_type_assessment": "database_record_is_not_a_journal_research_paper"})
    for paper in csv.DictReader((ROOT / "data/papers_reviewed_INCOMPLETE.csv").open()):
        records[paper["doi"]].update({"review_status": "included_in_reviewed_subset", "credit_status": paper["credit_status"]})
    decisions = screening_decisions()
    for doi, decision in decisions.items():
        record = records[doi]
        record.update({"relevance_review_reason": decision["reason"], "relevance_review_evidence": decision.get("evidence", "")})
        if record["review_status"] in {"excluded_publisher_date_outside_window", "duplicate_source_record"}:
            continue
        if decision["decision"] == "exclude_relevance":
            record.update({"review_status": "excluded_relevance_after_review", "credit_status": "not_eligible"})
        elif decision["decision"] == "needs_fuller_relevance_review":
            record["review_status"] = "abstract_reviewed_relevance_unresolved"
        elif decision["decision"] == "needs_abstract_review":
            record["review_status"] = "title_screened_abstract_review_pending"
        elif decision["decision"] == "exclude_document_type":
            record.update({"review_status": "excluded_nonoriginal_after_review", "credit_status": "not_eligible"})
        elif decision["decision"] == "exclude_date":
            record.update({"review_status": "excluded_publisher_date_outside_window", "credit_status": "not_eligible"})
        elif decision["decision"] == "include_pending_primary_evidence":
            record.update({"review_status": "evolutionary_relevance_confirmed_primary_evidence_pending", "credit_status": "not_assessed"})
        elif decision["decision"] == "include_pending_date_policy":
            record.update({"review_status": "evolutionary_relevance_confirmed_date_policy_pending", "credit_status": "not_assessed"})
    rows = sorted(records.values(), key=lambda r: (r["journal"], r["record_id"]))
    for filename, content in [("screening_audit_INCOMPLETE.csv", rows), ("journal_coverage_INCOMPLETE.csv", counts)]:
        with (ROOT / "data" / filename).open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(content[0]))
            writer.writeheader()
            writer.writerows(content)
    status = {"publication_start": START, "publication_end": END,
              "database_records": sum(c["database_records"] for c in counts),
              "openalex_records": sum(c["openalex_records"] for c in counts),
              "crossref_online_records": sum(c["crossref_online_records"] for c in counts),
              "combined_distinct_records": len(rows),
              "records_seen_in_publisher_inventory": sum(r["seen_in_publisher_inventory"] == "true" for r in rows),
              "reviewed_included_papers": sum(r["review_status"] == "included_in_reviewed_subset" for r in rows),
              "reviewed_excluded_relevance": sum(r["review_status"] == "excluded_relevance_after_review" for r in rows),
              "abstract_reviewed_relevance_unresolved": sum(r["review_status"] == "abstract_reviewed_relevance_unresolved" for r in rows),
              "nonoriginal_by_publisher_type": sum(r["review_status"] == "excluded_nonoriginal_publisher_type" for r in rows),
              "nonoriginal_by_database_type": sum(r["review_status"] == "excluded_nonoriginal_database_type" for r in rows),
              "full_audit_complete": False, "top100_produced": False}
    (ROOT / "data/audit_status.json").write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps(status))


if __name__ == "__main__":
    main()
