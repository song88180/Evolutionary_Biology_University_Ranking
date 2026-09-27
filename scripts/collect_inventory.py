"""Collect publication inventories; never infer inclusion or corresponding authors.

Publisher inventories are primary discovery sources. Europe PMC records are
supplementary discovery records and need reconciliation against publisher pages.
"""
import argparse
import concurrent.futures
import csv
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from study_config import START, END, INVENTORY

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "sources"
JOURNALS = {
    "nature": ("Nature", "0028-0836"),
    "science": ("Science", "0036-8075"),
    "cell": ("Cell", "0092-8674"),
    "natecolevol": ("Nature Ecology & Evolution", "2397-334X"),
    "ng": ("Nature Genetics", "1061-4036"),
    "nathumbehav": ("Nature Human Behaviour", "2397-3374"),
    "pnas": ("Proceedings of the National Academy of Sciences", "0027-8424"),
    "sciadv": ("Science Advances", "2375-2548"),
    "ncomms": ("Nature Communications", "2041-1723"),
    "cub": ("Current Biology", "0960-9822"),
    "mbe": ("Molecular Biology and Evolution", "0737-4038"),
}


def fetch(url, headers=None):
    key = hashlib.sha256(url.encode()).hexdigest()
    body = CACHE / (key + ".body")
    meta = CACHE / (key + ".json")
    if body.exists() and meta.exists():
        return body.read_text()
    CACHE.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=45, headers={
                "User-Agent": "EvoRankingResearch/0.1 (bibliographic research)",
                **(headers or {})})
            response.raise_for_status()
            text = response.text
            if "<title>Just a moment" in text:
                raise RuntimeError("Publisher access challenge")
            body.write_text(text)
            meta.write_text(json.dumps({
                "requested_url": url, "final_url": response.url,
                "retrieved_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "sha256": hashlib.sha256(text.encode()).hexdigest(),
                "http_status": response.status_code,
            }, indent=2) + "\n")
            return text
        except requests.RequestException as error:
            # Do not repeatedly hit a denied, missing, or rate-limited endpoint.
            if error.response is not None and error.response.status_code in (401, 403, 404, 429):
                raise
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def write_csv(name, rows, columns):
    directory = INVENTORY
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / name).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def nature_page(slug, page, article_type=None, year=2026):
    url = f"https://www.nature.com/{slug}/articles?year={year}&page={page}"
    if article_type:
        url += "&type=" + article_type
    soup = BeautifulSoup(fetch(url), "html.parser")
    rows = []
    for card in soup.select("article.c-card"):
        link = card.select_one(".c-card__title a")
        date = card.select_one("time[datetime]")
        kind = card.select_one(".c-meta__type")
        summary = card.select_one(".c-card__summary")
        if not link or not date or not kind:
            raise ValueError(f"Incomplete article card on {url}")
        article_url = urljoin(url, link["href"])
        rows.append({
            "journal": JOURNALS[slug][0],
            "doi": "10.1038/" + article_url.rsplit("/", 1)[-1],
            "title": link.get_text(" ", strip=True),
            "publication_date": date["datetime"][:10],
            "article_type": kind.get_text(" ", strip=True),
            "publisher_summary": summary.get_text(" ", strip=True) if summary else "",
            "article_url": article_url, "inventory_url": url,
            "review_status": "unreviewed",
        })
    pages = [int(x) for a in soup.select("a[href]")
             for x in parse_qs(urlparse(a["href"]).query).get("page", []) if x.isdigit()]
    if not rows:
        raise ValueError(f"No article cards found on {url}")
    return rows, max(pages, default=1)


def nature_inventory(slug, cutoff, article_type=None, start=START, year=2026):
    first, last = nature_page(slug, 1, article_type, year)
    print(f"{slug}: {last} publisher inventory pages", flush=True)
    rows = first[:]
    errors = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        pending = {executor.submit(nature_page, slug, page, article_type, year): page
                   for page in range(2, last + 1)}
        for future in concurrent.futures.as_completed(pending):
            page = pending[future]
            try:
                batch, _ = future.result()
                rows.extend(batch)
            except Exception as error:
                errors.append({"page": page, "error": str(error)})
            if page % 20 == 0:
                print(f"{slug}: page {page}/{last}; {len(rows)} records", flush=True)
    all_count = len(rows)
    dedup = {row["doi"]: row for row in rows if start <= row["publication_date"] <= cutoff}
    rows = sorted(dedup.values(), key=lambda row: (row["publication_date"], row["doi"]))
    suffix = f"_{year}" + ("_" + article_type if article_type else "")
    write_csv(f"{slug}{suffix}_publisher.csv", rows, list(first[0]))
    status = {"journal": JOURNALS[slug][0], "publisher_pages_expected": last,
              "publisher_pages_fetched": last - len(errors), "errors": errors,
              "raw_records": all_count, "unique_in_window": len(rows),
              "inventory_completeness_verified": False,
              "start": start, "cutoff": cutoff, "relevance_review_complete": False,
              "corresponding_author_review_complete": False}
    (INVENTORY / f"{slug}{suffix}_coverage.json").write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps(status), flush=True)


def epmc_inventory(slug, cutoff, start=START):
    name, issn = JOURNALS[slug]
    # Broad date discovery: publisher dates determine final eligibility.
    query = f'ISSN:{issn} AND FIRST_PDATE:[{start} TO {cutoff}]'
    cursor = "*"
    records = {}
    total = None
    while True:
        url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urlencode({
            "query": query, "format": "json", "resultType": "core",
            "pageSize": 1000, "cursorMark": cursor,
        })
        payload = json.loads(fetch(url))
        total = payload["hitCount"]
        batch = payload.get("resultList", {}).get("result", [])
        for record in batch:
            records[(record.get("source"), record["id"])] = record
        print(f"{slug}: Europe PMC {len(records)}/{total}", flush=True)
        next_cursor = payload.get("nextCursorMark")
        if not batch or not next_cursor or next_cursor == cursor or len(records) >= total:
            break
        cursor = next_cursor
    directory = INVENTORY
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{slug}_epmc.json").write_text(json.dumps({
        "query": query, "expected_hits": total, "records": list(records.values()),
        "role": "Supplementary discovery only; not proof of publisher completeness or correspondence."
    }, ensure_ascii=False) + "\n")
    rows = []
    for record in records.values():
        rows.append({
            "journal": name, "doi": record.get("doi", ""),
            "title": record.get("title", ""),
            "publication_date": record.get("firstPublicationDate", ""),
            "publication_types": " | ".join(record.get("pubTypeList", {}).get("pubType", [])),
            "abstract": BeautifulSoup(record.get("abstractText", ""), "html.parser").get_text(" ", strip=True),
            "pmid": record.get("id", "") if record.get("source") == "MED" else "",
            "pmcid": record.get("pmcid", ""), "review_status": "unreviewed",
        })
    if rows:
        write_csv(f"{slug}_epmc.csv", rows, list(rows[0]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["nature", "epmc"])
    parser.add_argument("journals", nargs="+", choices=JOURNALS)
    parser.add_argument("--start", default=START)
    parser.add_argument("--cutoff", default=END)
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--type", help="Publisher article-type filter for reconciliation")
    args = parser.parse_args()
    for slug in args.journals:
        try:
            if args.mode == "nature":
                nature_inventory(slug, args.cutoff, args.type, args.start, args.year)
            else:
                epmc_inventory(slug, args.cutoff, args.start)
        except Exception as error:
            print(f"FAILED {slug}: {error}", flush=True)
            directory = INVENTORY
            directory.mkdir(parents=True, exist_ok=True)
            (directory / f"{slug}_{args.mode}_failure.json").write_text(
                json.dumps({"journal": JOURNALS[slug][0], "error": str(error)}, indent=2) + "\n")
