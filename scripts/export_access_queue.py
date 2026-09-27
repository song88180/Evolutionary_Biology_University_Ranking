"""Export records for automated correspondence checks, not a download list."""
import csv
import json
from pathlib import Path
import re
from study_config import INVENTORY

ROOT = Path(__file__).resolve().parents[1]
rows = []
for slug in ["science", "cub", "pnas", "cell"]:
    source = INVENTORY / f"{slug}_epmc.json"
    for record in json.loads(source.read_text())["records"]:
        title = record.get("title", "")
        kinds = record.get("pubTypeList", {}).get("pubType", [])
        if record.get("pmcid") or "Review" in kinds:
            continue
        if not re.search(r"evolution|speciation|natural selection|ancient DNA", title, re.I):
            continue
        rows.append({"journal_key": slug, "doi": record.get("doi", ""), "title": title,
                     "database_first_publication_date": record.get("firstPublicationDate", ""),
                     "pmid": record["id"], "publisher_url": "https://doi.org/" + record.get("doi", ""),
                     "known_fulltext_links_json": json.dumps(record.get("fullTextUrlList", {})),
                     "status": "no_PMC_identifier_in_database; automated_correspondence_lookup_pending",
                     "relevance_status": "title_flag_only_not_final_inclusion"})
with (ROOT / "data/fulltext_access_candidates.csv").open("w", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
print(f"Saved {len(rows)} automated follow-ups. No user downloads requested.")
