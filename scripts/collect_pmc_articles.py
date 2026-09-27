"""Extract explicit corresponding-author links from repository JATS records."""
import argparse
from collections import Counter
import concurrent.futures
import csv
import hashlib
import json
import re
import xml.etree.ElementTree as ET

from collect_inventory import CACHE, ROOT, fetch
from study_config import screening_decisions


def text(element):
    return " ".join("".join(element.itertext()).split()) if element is not None else ""


def affiliation_text(element):
    node = ET.fromstring(ET.tostring(element))
    for label in list(node):
        if label.tag == "label" or (label.tag == "sup" and re.fullmatch(r"[a-zA-Z0-9,*†‡ ]+", text(label))):
            node.text = (node.text or "") + (label.tail or "")
            node.remove(label)
    return text(node)


def is_contribution_note(address):
    # Some publisher JATS encodes contribution footnotes as numbered <aff>s.
    # Only these exact non-address statements are excluded; preserve all others.
    return address.casefold().rstrip(".") in {
        "lead contact", "these authors contributed equally", "these authors contributed equally to this work",
        "senior authors"
    }


def parse_article(xml, row):
    root = ET.fromstring(xml)
    meta = root.find("front/article-meta")
    if meta is None:
        raise ValueError("JATS article metadata missing")
    doi = next((text(e).lower() for e in meta.findall("article-id") if e.get("pub-id-type") == "doi"), "")
    if doi != row["doi"].lower():
        raise ValueError("Repository DOI does not match requested paper")
    affiliations = {e.get("id"): e for e in meta.findall(".//aff") if e.get("id")}
    correspondence = {e.get("id"): e for e in meta.findall(".//corresp") if e.get("id")}
    correspondence.update({e.get("id"): e for e in meta.findall(".//fn")
                           if e.get("id") and (e.get("fn-type") == "corresp"
                           or re.search(r"\bcorresponding authors?\b|\bcorrespondence\s*:|\bcorrespondence (?:to|(?:may|should|must|can) be addressed)\b", text(e), re.I)
                           or (text(e.find("label")) == "✉" and e.find(".//email") is not None))})
    authors = []
    non_affiliation_notes = []
    represented = set()
    for author in meta.findall(".//contrib-group/contrib"):
        if author.get("contrib-type") not in ("author", None):
            continue
        refs = {rid for e in author.findall(".//xref") for rid in e.get("rid", "").split()}
        corr_refs = refs & correspondence.keys()
        if author.get("corresp") != "yes" and not corr_refs:
            continue
        represented.update(corr_refs)
        name_element = author.find("name")
        if name_element is None:
            name_element = author.find("string-name")
        if name_element is None:
            raise ValueError("Corresponding contributor lacks an individual name")
        name = " ".join(filter(None, [text(name_element.find("given-names")), text(name_element.find("surname")), text(name_element.find("suffix"))]))
        linked = []
        aff_refs = {rid for e in author.findall(".//xref") if e.get("ref-type") == "aff" for rid in e.get("rid", "").split()}
        for rid in sorted(aff_refs):
            if rid not in affiliations:
                raise ValueError("Missing linked affiliation " + rid)
            address = affiliation_text(affiliations[rid])
            if is_contribution_note(address):
                non_affiliation_notes.append({"author": name, "note_id": rid, "text": address})
            else:
                linked.append({"affiliation_id": rid, "address": address})
        # Inline <aff> children are explicit author–affiliation links too.
        for number, node in enumerate(author.findall("aff"), 1):
            address = affiliation_text(node)
            if is_contribution_note(address):
                non_affiliation_notes.append({"author": name, "note_id": node.get("id", ""), "text": address})
            else:
                linked.append({"affiliation_id": node.get("id", f"inline-{number}"), "address": address})
        if not linked or not name:
            raise ValueError("Corresponding author lacks explicit affiliation links")
        authors.append({"name": name, "affiliations": linked})
    if not authors:
        raise ValueError("No explicitly linked corresponding authors in JATS")
    # A correspondence note unlinked to the byline may hide additional authors.
    unlinked = sorted(correspondence.keys() - represented)
    dates = []
    date_evidence = "repository_explicit_electronic_publication_date"
    for date in meta.findall("pub-date"):
        if date.get("pub-type") != "epub" and not (date.get("publication-format") == "electronic" and date.get("date-type") in ("pub", "publication")):
            continue
        try:
            dates.append(f"{int(date.findtext('year')):04d}-{int(date.findtext('month')):02d}-{int(date.findtext('day')):02d}")
        except (ValueError, TypeError):
            pass
    if not dates and row.get("journal") == "Science Advances":
        # AAAS identifies Science Advances as online-only. An untyped
        # article publication date therefore describes electronic publication.
        # Collection/issue dates remain excluded.
        for date in meta.findall("pub-date"):
            if date.attrib:
                continue
            try:
                dates.append(f"{int(date.findtext('year')):04d}-{int(date.findtext('month')):02d}-{int(date.findtext('day')):02d}")
            except (ValueError, TypeError):
                pass
        if dates:
            date_evidence = "repository_publication_date_of_online_only_journal"
    status = "explicit_repository_links_parsed" if dates and not unlinked else "repository_links_need_review"
    return {**row, "doi": doi, "title": text(meta.find("title-group/article-title")),
            "publisher_date": min(dates) if dates else "", "article_type": root.get("article-type", ""),
            "date_evidence": date_evidence if dates else "online_date_unresolved",
            "abstract": " ".join(text(e) for e in meta.findall("abstract")),
            "article_url": "https://doi.org/" + doi,
            "source_url": f"https://www.ebi.ac.uk/europepmc/webservices/rest/{row['pmcid']}/fullTextXML",
            "corresponding_authors": authors, "correspondence_statement": " | ".join(text(e) for e in correspondence.values()),
            "unlinked_correspondence_notes": unlinked, "extraction_status": status,
            "non_affiliation_notes": non_affiliation_notes,
            "relevance_status": "unreviewed", "normalization_status": "unreviewed"}


def collect(row, cached_only=False, reparse=False):
    target = ROOT / "data/articles" / (row["doi"].split("/")[-1] + ".json")
    if target.exists():
        existing = json.loads(target.read_text())
        if existing.get("extraction_status") == "explicit_publisher_links_parsed" or (not reparse and existing.get("extraction_status") == "explicit_repository_links_parsed"):
            return {"doi": row["doi"], "status": "existing_explicit_evidence"}
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{row['pmcid']}/fullTextXML"
    if cached_only and not (CACHE / (hashlib.sha256(url.encode()).hexdigest() + ".body")).exists():
        return {"doi": row["doi"], "pmcid": row["pmcid"], "status": "not_cached", "source_url": url}
    try:
        result = parse_article(fetch(url), row)
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        return {"doi": row["doi"], "pmcid": row["pmcid"], "status": result["extraction_status"], "source_url": url}
    except Exception as error:
        return {"doi": row["doi"], "pmcid": row["pmcid"], "status": "extraction_failed", "source_url": url, "error": str(error)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", action="append", help="Exact journal name; repeat to select several")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--cached-only", action="store_true")
    parser.add_argument("--reparse", action="store_true", help="Rebuild repository evidence with the current parser; preserve explicit publisher evidence")
    parser.add_argument("--review-candidates", action="store_true", help="Collect pending screened candidates regardless of keyword priority")
    args = parser.parse_args()
    decisions = screening_decisions()
    rows = [r for r in csv.DictReader((ROOT / "data/screening_audit_INCOMPLETE.csv").open())
            if r["pmcid"] and r["doi"] and
            (decisions.get(r['doi'], {}).get('decision') in {'include_pending_primary_evidence', 'needs_abstract_review', 'needs_fuller_relevance_review'}
             if args.review_candidates else r["priority_only_not_classification"] == "early_review")
            and (not args.journal or r["journal"] in args.journal)]
    if args.limit:
        rows = rows[:args.limit]
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        for result in executor.map(lambda row: collect(row, args.cached_only, args.reparse), rows):
            results.append(result)
            if len(results) % 50 == 0:
                print(f"PMC {len(results)}/{len(rows)}: {dict(Counter(r['status'] for r in results))}", flush=True)
    path = ROOT / "data/pmc_collection_status.json"
    previous = {r["doi"]: r for r in json.loads(path.read_text())} if path.exists() else {}
    previous.update({r["doi"]: r for r in results if r["status"] != "not_cached" or r["doi"] not in previous})
    path.write_text(json.dumps(list(previous.values()), indent=2) + "\n")
    print(json.dumps(dict(Counter(r["status"] for r in results))), flush=True)
