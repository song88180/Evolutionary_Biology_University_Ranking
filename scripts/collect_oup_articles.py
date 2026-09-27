"""Read explicit OUP author cards from the publisher's public article view.

The minimal view is the public destination of Oxford Academic redirects. Only
authors with a correspondence card are selected; email-only authors are not.
"""
import argparse
from datetime import datetime
import json
import re

from bs4 import BeautifulSoup
from collect_inventory import ROOT, fetch


def parse(html, doi, url):
    # Requests can default to Latin-1 for a UTF-8 HTML response without charset.
    if "â\x80" in html or "Ã" in html:
        try:
            html = html.encode("latin1").decode("utf8")
        except (UnicodeError, ValueError):
            pass
    soup = BeautifulSoup(html, "html.parser")
    citation = soup.select_one(".ww-citation-primary")
    if not citation or not any(a.get("href", "").lower().rstrip("/") == "https://doi.org/" + doi.lower() for a in citation.select("a[href]")):
        raise ValueError("Publisher citation DOI mismatch")
    title = soup.select_one("h1.article-title-main")
    dates = [x.find_next_sibling(class_="citation-date") for x in soup.select(".citation-label") if x.get_text(strip=True) == "Published:"]
    if not title or len(dates) != 1 or dates[0] is None:
        raise ValueError("Missing unique publisher title/date")
    date = datetime.strptime(dates[0].get_text(strip=True), "%d %B %Y").date().isoformat()
    authors, statements = [], []
    for card in soup.select(".al-author-name.js-flyout-wrap, .al-author-name-more.js-flyout-wrap"):
        note = card.select_one(".info-author-correspondence")
        if not note or not note.get_text(strip=True):
            continue
        name = card.select_one("a.linked-name")
        affiliations = [{"affiliation_id": f"author-card-{i+1}", "address": a.get_text(" ", strip=True)} for i, a in enumerate(card.select(".info-card-affilitation .aff"))]
        if not name or not affiliations:
            raise ValueError("Incomplete corresponding-author card")
        authors.append({"name": name.get_text(" ", strip=True), "affiliations": affiliations})
        statements.append(note.get_text(" ", strip=True))
    if not authors:
        raise ValueError("No explicit publisher correspondence cards")
    abstract = soup.select_one("section.abstract")
    accepted = bool(re.search(r"Accepted manuscript", soup.get_text(" ", strip=True), re.I))
    return {"doi": doi, "journal": "Molecular Biology and Evolution", "title": title.get_text(" ", strip=True),
            "publisher_title": title.get_text(" ", strip=True), "article_url": url, "source_url": url,
            "publisher_date": date, "date_evidence": "publisher_explicit_published_date",
            "publication_version": "accepted_manuscript" if accepted else "publisher_version_unstated",
            "article_type": "Journal Article", "article_type_review_required": True,
            "abstract": abstract.get_text(" ", strip=True) if abstract else "",
            "corresponding_authors": authors, "correspondence_statement": " | ".join(dict.fromkeys(statements)),
            "extraction_status": "explicit_publisher_links_parsed", "relevance_status": "unreviewed"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("doi")
    parser.add_argument("publisher_article_id", type=int)
    args = parser.parse_args()
    url = f"https://oup.silverchair-cdn.com/article-minimal/{args.publisher_article_id}"
    result = parse(fetch(url), args.doi, url)
    target = ROOT / "data/articles" / (args.doi.split("/")[-1] + ".json")
    if target.exists():
        previous = json.loads(target.read_text())
        if previous.get("extraction_status") in ("explicit_publisher_links_parsed", "explicit_repository_links_parsed"):
            raise ValueError("Existing explicit evidence preserved; review before replacing")
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"doi": args.doi, "date": result["publisher_date"], "corresponding_authors": len(result["corresponding_authors"]), "version": result["publication_version"]}))


if __name__ == "__main__":
    main()
