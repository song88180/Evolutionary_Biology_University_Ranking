"""Build the standalone website data from the reviewed ranking exports."""

import csv
from fractions import Fraction
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SITE = ROOT / "website"
ASSETS = SITE / "assets"
FINAL_STATUS = "FINAL_SNAPSHOT_2026-09-27"


def rows(name):
    with (DATA / name).open(newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, items, columns):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(items)


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    ranking = rows("top100_PROVISIONAL.csv")
    contributions = rows("top100_paper_contributions_PROVISIONAL.csv")
    included = rows("papers_reviewed_PROVISIONAL.csv")
    journals = rows("journal_impact_factors.csv")
    chinese_names = json.loads((SITE / "university_names_zh.json").read_text())
    status = json.loads((DATA / "provisional_ranking_status.json").read_text())
    assert len(ranking) == 100
    assert status["included_papers"] == status["fully_allocated_papers"] == 2378
    assert status["fallback_papers_included"] == 347
    assert len(included) == status["included_papers"]
    assert len({paper["doi"] for paper in included}) == len(included)
    assert all(paper["credit_status"] == "ready" for paper in included)
    assert set(chinese_names) == {row["institution_id"] for row in ranking}, "Every ranked university needs one Chinese name"

    by_id = {r["institution_id"]: r for r in ranking}
    grouped = {key: [] for key in by_id}
    for paper in contributions:
        key = paper["institution_id"]
        assert key in by_id
        grouped[key].append({
            "doi": paper["doi"],
            "title": paper["article_title"],
            "journal": paper["journal"],
            "date": paper["publication_date"],
            "points": float(paper["impact_factor_points"]),
            "fraction": paper["fraction_exact"],
            "url": paper["article_url"],
            "source": "OpenAlex" if paper["correspondence_evidence_status"] == "explicit_openalex_correspondence_PROVISIONAL" else "Publisher / repository",
        })
    for rank in ranking:
        key = rank["institution_id"]
        assert len(grouped[key]) == int(rank["qualifying_papers"]), key
        assert sum((Fraction(p["impact_factor_points_exact"]) for p in contributions if p["institution_id"] == key), Fraction()) == Fraction(rank["total_impact_factor_score_exact"]), key
        grouped[key].sort(key=lambda p: (-p["points"], p["title"]))

    payload = {
        "title": "Evolutionary Biology University Ranking 2026",
        "publicationStart": "2025-09-24",
        "publicationEnd": "2026-09-24",
        "finalized": "2026-09-27",
        "includedPapers": status["included_papers"],
        "openAlexFallbackPapers": status["fallback_papers_included"],
        "ranking": [{
            "rank": int(r["rank"]),
            "id": r["institution_id"],
            "name": r["university"],
            "nameZh": chinese_names[r["institution_id"]],
            "score": float(r["total_impact_factor_score"]),
            "papers": int(r["qualifying_papers"]),
            "full": int(r["full_credit_papers"]),
            "fractional": int(r["fractional_credit_papers"]),
            "openAlexPapers": int(r["openalex_fallback_papers"]),
        } for r in ranking],
        "journals": [{"name": j["journal"], "impactFactor": float(j["impact_factor"])}
                     for j in sorted(journals, key=lambda item: (-float(item["impact_factor"]), item["journal"]))],
    }
    (ASSETS / "ranking-data.js").write_text("window.RANKING_DATA = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n")
    paper_payload = {
        "included": [{
            "doi": paper["doi"],
            "title": paper["article_title"],
            "journal": paper["journal"],
            "date": paper["publication_date"],
            "authors": paper["corresponding_authors"],
            "reason": paper["evolutionary_justification"],
            "url": paper["article_url"],
            "source": "OpenAlex" if paper["correspondence_evidence_status"] == "explicit_openalex_correspondence_PROVISIONAL" else "Publisher / repository",
        } for paper in sorted(included, key=lambda p: (p["publication_date"], p["doi"]), reverse=True)],
        "contributions": grouped,
    }
    (ASSETS / "paper-data.js").write_text("window.PAPER_DATA = " + json.dumps(paper_payload, ensure_ascii=False, separators=(",", ":")) + ";\n")

    ranking_columns = [key for key in ranking[0] if key != "dataset_status"] + ["dataset_status"]
    paper_columns = [key for key in contributions[0] if key != "dataset_status"] + ["dataset_status"]
    included_columns = [key for key in included[0] if key != "dataset_status"] + ["dataset_status"]
    write_csv(ASSETS / "ranking.csv", [{**r, "dataset_status": FINAL_STATUS} for r in ranking], ranking_columns)
    write_csv(ASSETS / "paper-contributions.csv", [{**p, "dataset_status": FINAL_STATUS} for p in contributions], paper_columns)
    write_csv(ASSETS / "included-papers.csv", [{**p, "dataset_status": FINAL_STATUS} for p in included], included_columns)
    print(f"Built website data: {len(ranking)} institutions, {len(included)} included papers, {len(contributions)} top-100 paper-credit rows")


if __name__ == "__main__":
    main()
