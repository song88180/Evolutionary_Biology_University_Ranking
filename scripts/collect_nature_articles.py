"""Extract explicit publisher correspondence links for an inventory.

Extraction is not a relevance decision or an institution normalization decision.
"""
import concurrent.futures
import csv
import json
from pathlib import Path
import re
import sys

from bs4 import BeautifulSoup
from collect_inventory import ROOT, fetch

RESEARCH_TYPES = {"Article", "Letter", "Brief Communication", "Analysis", "Technical Report", "Resource", "Matters Arising", "Registered Report"}


def article(row):
    soup = BeautifulSoup(fetch(row["article_url"]), "html.parser")
    doi_meta = soup.find("meta", attrs={"name": "citation_doi"})
    if doi_meta is None or doi_meta.get("content", "").lower() != row["doi"].lower():
        raise ValueError("Publisher DOI does not match requested paper")
    type_meta = soup.find("meta", attrs={"name": "citation_article_type"})
    article_type = type_meta.get("content", "") if type_meta else row.get("article_type", "")
    data = {}
    for script in soup.select('script[type="application/ld+json"]'):
        obj = json.loads(script.string or script.get_text())
        if isinstance(obj, dict) and isinstance(obj.get("mainEntity"), dict):
            data = obj["mainEntity"]
            break
    if article_type not in RESEARCH_TYPES:
        return {**row, "publisher_title": data.get("headline", ""),
                "publisher_date": data.get("datePublished", "")[:10],
                "article_type": article_type, "extraction_status": "publisher_type_metadata_parsed",
                "corresponding_authors": [], "relevance_status": "unreviewed"}
    corr = soup.find(id="corresponding-author-list")
    if corr is None:
        raise ValueError("Explicit corresponding-author section missing")
    names = [a.get_text(" ", strip=True) for a in corr.select("a")]
    names = list(dict.fromkeys(names))
    if not names:
        raise ValueError("No explicitly named corresponding authors")
    authors = []
    for name in names:
        # Use the HTML affiliation numbering to preserve the complete verbatim
        # address, and to avoid attaching other authors' institutions.
        author_li = next((li for li in soup.select(".c-article-authors-search > li")
                          if li.select_one(".js-search-name") and
                          li.select_one(".js-search-name").get_text(" ", strip=True) == name), None)
        affiliations = []
        if author_li:
            for aff_id in re.findall(r"Aff\d+", author_li.get("id", "")):
                aff = soup.find(id=aff_id)
                address = aff.select_one(".c-article-author-affiliation__address") if aff else None
                if address:
                    affiliations.append({"affiliation_id": aff_id, "address": address.get_text(" ", strip=True)})
        if not affiliations:
            raise ValueError(f"Cannot resolve affiliation links for {name}")
        authors.append({"name": name, "affiliations": affiliations})
    abstract = soup.find(id="Abs1-content")
    return {**row, "publisher_title": data.get("headline", ""),
            "article_type": article_type,
            "publisher_date": data.get("datePublished", "")[:10],
            "abstract": abstract.get_text(" ", strip=True) if abstract else data.get("description", ""),
            "correspondence_statement": corr.get_text(" ", strip=True),
            "corresponding_authors": authors, "keywords": data.get("keywords", []),
            "extraction_status": "explicit_publisher_links_parsed",
            "relevance_status": "unreviewed", "normalization_status": "unreviewed"}


def main(inventory):
    with open(inventory) as stream:
        rows = [r for r in csv.DictReader(stream) if r["article_type"] in RESEARCH_TYPES]
    target = ROOT / "data" / "articles"
    target.mkdir(parents=True, exist_ok=True)
    completed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        pending = {executor.submit(article, row): row for row in rows}
        for future in concurrent.futures.as_completed(pending):
            row = pending[future]
            try:
                result = future.result()
            except Exception as error:
                result = {**row, "extraction_status": "failed", "error": str(error)}
            (target / (row["doi"].split("/")[-1] + ".json")).write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n")
            completed += 1
            if completed % 20 == 0:
                print(f"{inventory}: {completed}/{len(rows)} article pages processed", flush=True)
    print(f"Processed {len(rows)} article pages from {inventory}", flush=True)


if __name__ == "__main__":
    for inventory in sys.argv[1:]:
        main(inventory)
