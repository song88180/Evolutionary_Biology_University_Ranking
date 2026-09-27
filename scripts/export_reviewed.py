"""Export the reviewed subset without claiming an exhaustive ranking.

Conservative normalization: only explicit, unambiguous university parents are
resolved automatically. Joint/independent affiliations hold the entire paper
out of point totals until a complete manually verified mapping is provided.
"""
import argparse
import csv
from fractions import Fraction
import json
from pathlib import Path
import re
import unicodedata
from study_config import START, END, screening_decisions

ROOT = Path(__file__).resolve().parents[1]


def normalized(value):
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def distribute(jif, institution_ids):
    ids = sorted(set(institution_ids))
    if not ids:
        raise ValueError("All corresponding-author institutions must be resolved")
    weight = Fraction(str(jif))
    if weight <= 0:
        raise ValueError("Impact factor must be positive")
    return {key: weight / len(ids) for key in ids}


def university_matches(address, needles):
    value = " " + normalized(address) + " "
    hits = []
    for needle, key in needles.items():
        token = " " + needle + " "
        start = value.find(token)
        while start >= 0:
            hits.append((start + 1, start + 1 + len(needle), key))
            start = value.find(token, start + 1)
    # South China Agricultural University must not also match the shorter
    # China Agricultural University name inside the very same occurrence.
    return {key for start, end, key in hits
            if not any(a <= start and end <= b and (a, b) != (start, end) for a, b, _ in hits)}


def save(name, columns, rows):
    path = ROOT / "data" / name
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def provisional_records(decisions):
    """Load separately reviewed eligibility; correspondence permission is not eligibility."""
    from prepare_openalex_fallback import PRIMARY, provisional_correspondence
    from collect_openalex_inventory import work_cache_path
    evidence_path = ROOT / 'data/openalex_fallback_correspondence.json'
    ledger_path = ROOT / 'data/fallback_eligibility_decisions.json'
    if not ledger_path.exists():
        return {}
    evidence = json.loads(evidence_path.read_text())
    ledger = json.loads(ledger_path.read_text())
    audit = {r['doi']: r for r in csv.DictReader((ROOT / 'data/screening_audit_INCOMPLETE.csv').open()) if r['doi']}
    records = {}
    for doi, review in ledger.items():
        if review['decision'] != 'include':
            continue
        if decisions.get(doi, {}).get('decision') not in {'include', 'include_pending_primary_evidence'}:
            raise ValueError('Fallback cannot bypass scientific screening: ' + doi)
        path = ROOT / 'data/articles' / (doi.split('/')[-1] + '.json')
        primary = json.loads(path.read_text()) if path.exists() else {}
        if primary.get('extraction_status') in PRIMARY:
            # Never substitute lower-quality evidence; let the primary ledger
            # determine inclusion after any remaining eligibility review.
            continue
        cached = json.loads(work_cache_path(doi).read_text())
        fresh = provisional_correspondence(cached['work'], doi, primary)
        if doi not in evidence or not evidence[doi].get('primary_access_limitation'):
            raise ValueError('Fallback lacks documented primary-access limitation: ' + doi)
        if not (review.get('original_research_evidence') and review.get('publication_date_source_url')
                and START <= review.get('publisher_date', '') <= END):
            raise ValueError('Fallback eligibility review incomplete: ' + doi)
        records[doi.split('/')[-1]] = {**audit[doi], **fresh,
            'publisher_date': review['publisher_date'],
            'article_type': 'original_research_confirmed_by_abstract_review',
            'date_evidence': review['date_evidence'],
            'publication_date_source_url': review['publication_date_source_url'],
            'original_research_evidence': review['original_research_evidence'],
            'primary_access_limitation': evidence[doi]['primary_access_limitation'],
            'article_url': 'https://doi.org/' + doi}
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provisional', action='store_true', help='Add explicitly authorized OpenAlex fallback after separate eligibility review')
    args = parser.parse_args()
    with (ROOT / "data/arwu_2026_top1000.csv").open() as stream:
        universities = {r["institution_id"]: r["university"] for r in csv.DictReader(stream)}
    outside = json.loads((ROOT / "data/institutions_outside_pool.json").read_text())
    if set(outside) & set(universities):
        raise ValueError("Outside-pool institution ID overlaps the ARWU pool")
    institution_names = {**universities, **outside}
    overrides = json.loads((ROOT / "data/affiliation_overrides.json").read_text())
    for override in overrides.values():
        ids = override["institution_ids"]
        if ids == [] and override.get("administrative_zero_credit"):
            # Explicitly reviewed: this address names only a government ministry,
            # regulatory agency or pure grant-funding body (not itself research-
            # performing) and contributes no institution to the corresponding
            # author's credited set. Other affiliations of the same author (or
            # other authors) still supply the paper's real institution ids.
            continue
        if not ids or set(ids) - set(institution_names):
            raise ValueError("Invalid manual affiliation override")
        scope = override.get("only_for_dois")
        if scope is not None and (not isinstance(scope, list) or not scope
                                  or any(not isinstance(doi, str) or not doi.startswith("10.") for doi in scope)
                                  or len(scope) != len(set(scope))):
            raise ValueError("Invalid DOI scope for manual affiliation override")
    joint_rules = json.loads((ROOT / "data/reviewed_joint_affiliation_rules.json").read_text())
    for rule in joint_rules.values():
        if (not rule['required_substring'] or not rule['only_for_dois']
                or not set(rule['required_ids']) <= set(rule['allowed_ids'])
                or set(rule['allowed_ids']) - set(institution_names)):
            raise ValueError("Invalid reviewed joint-affiliation rule")
    aliases = json.loads((ROOT / "data/institution_aliases.json").read_text())
    unknown = set(aliases.values()) - set(institution_names)
    if unknown:
        raise ValueError(f"Alias targets absent from institution registry: {unknown}")
    needles = {normalized(name): key for key, name in institution_names.items()}
    needles.update({normalized(name): key for name, key in aliases.items()})
    joint = re.compile(r"\b(CSIC|CNRS|INSERM|ICREA|CIBERSAM)\b|Centre National de la Recherche|Swiss Institute of Bioinformatics|Collegium|Biohub|Genomics Aotearoa|Boyce Thompson Institute|Shandong Laboratory|Peking[–-]Tsinghua|Institut Català de Paleontologia|Centre for Palaeogenetics|Senckenberg|Howard Hughes Medical Institute.*(?:University|Laboratory|Caltech)", re.I)
    inclusions = json.loads((ROOT / "data/nee_inclusions.json").read_text())
    decisions = screening_decisions()
    for doi, decision in decisions.items():
        article_id = doi.split("/")[-1]
        if decision["decision"] == "include":
            if article_id in inclusions:
                raise ValueError(f"Duplicate inclusion decision: {article_id}")
            inclusions[article_id] = decision["reason"]
    fallback = provisional_records(decisions) if args.provisional else {}
    for article_id, row in fallback.items():
        inclusions[article_id] = decisions[row['doi']]['reason']
    with (ROOT / "data/journal_impact_factors.csv").open() as stream:
        weights = {r["journal"]: r for r in csv.DictReader(stream)}
    if len({r["jif_data_year"] for r in weights.values()}) != 1:
        raise ValueError("All weights must use the same JIF data year")
    papers, credits, unresolved = [], [], []
    for article_id, rationale in inclusions.items():
        row = fallback.get(article_id) or json.loads((ROOT / "data/articles" / (article_id + ".json")).read_text())
        allowed = {"explicit_publisher_links_parsed", "explicit_repository_links_parsed"}
        if args.provisional:
            allowed.add('explicit_openalex_correspondence_PROVISIONAL')
        if row["extraction_status"] not in allowed:
            raise ValueError(f"Missing correspondence: {article_id}")
        if not START <= row["publisher_date"] <= END:
            raise ValueError(f"Publisher date out of range: {article_id}")
        if row.get("date_comparison") == "date_conflict":
            raise ValueError(f"Publication-date conflict requires review: {article_id}")
        weight = weights[row["journal"]]
        ids = set()
        pending = False
        mappings = []
        exempted = []
        for author in row["corresponding_authors"]:
            for aff in author["affiliations"]:
                address = aff["address"]
                if re.match(r"^Institut Universitaire de France(?:\b|\s*\()", address, re.I):
                    if len(author["affiliations"]) == 1:
                        raise ValueError(f"IUF membership without a home institution requires review: {row['doi']}")
                    # IUF is a membership/delegation programme for researchers
                    # who remain at their home university, not another employer.
                    exempted.append({"author": author["name"], "affiliation": address,
                                     "reason": "Institut Universitaire de France is a membership/delegation programme, not a home institution."})
                    continue
                if re.fullmatch(r"(?:SciLife Lab|SciLifeLab|Science for Life Laboratory)(?:,\s*(?:Uppsala|Solna|Stockholm),\s*Sweden)?", address, re.I):
                    if len(author["affiliations"]) == 1:
                        raise ValueError(f"Standalone SciLifeLab infrastructure affiliation requires review: {row['doi']}")
                    # SciLifeLab describes itself as a shared national research
                    # infrastructure, not an additional university or employer.
                    # Preserve the other explicit institutional affiliations.
                    exempted.append({"author": author["name"], "affiliation": address,
                                     "reason": "SciLifeLab is a shared national research infrastructure, not an additional employer."})
                    continue
                if re.match(r"^independent (?:researcher|scholar)(?:\b|,)", address, re.I):
                    if len(author["affiliations"]) != 1:
                        raise ValueError(f"Independent-author affiliation requires review: {row['doi']}")
                    # The user explicitly retains one non-university denominator
                    # share per independently affiliated corresponding author.
                    key = "outside:independent-author:" + row["doi"] + ":" + normalized(author["name"]).replace(" ", "-")
                    institution_names[key] = "Independent corresponding author: " + author["name"]
                    ids.add(key)
                    mappings.append({"author": author["name"], "affiliation": address,
                                     "institution_id": key, "institution": institution_names[key],
                                     "mapping_reason": "User-approved distinct non-university share for each independently affiliated corresponding author.",
                                     "mapping_source": "user_policy_2026-09-26"})
                    continue
                matches = university_matches(address, needles)
                override = overrides.get(address)
                if override and override.get('only_for_dois') is not None and row['doi'] not in override['only_for_dois']:
                    override = None
                if not override:
                    for rule in joint_rules.values():
                        if (row['doi'] in rule['only_for_dois']
                                and rule['required_substring'] in address):
                            if (not set(rule['required_ids']) <= matches
                                    or matches - set(rule['allowed_ids'])):
                                raise ValueError(f"Reviewed joint-affiliation rule no longer matches: {row['doi']}")
                            override = {**rule, 'institution_ids': sorted(matches)}
                            break
                if override:
                    if not override["institution_ids"]:
                        # administrative_zero_credit: explicitly reviewed as a
                        # government ministry/regulatory/funding body, not a
                        # research-performing institution; contributes no id but
                        # is still accounted for in the paper's audit trail.
                        exempted.append({"author": author["name"], "affiliation": address,
                                         "reason": override["reason"]})
                        continue
                    for key in override["institution_ids"]:
                        ids.add(key)
                        mappings.append({"author": author["name"], "affiliation": address,
                                         "institution_id": key, "institution": institution_names[key],
                                         "mapping_reason": override["reason"],
                                         "mapping_source": row["article_url"] if override["source_url"] == "publisher_corresponding_author_affiliation" else override["source_url"]})
                    continue
                # Different campuses stay distinct; ambiguous matches are not guessed.
                if len(matches) != 1 or joint.search(address):
                    pending = True
                    unresolved.append({"doi": row["doi"], "corresponding_author": author["name"],
                                       "affiliation": address, "reason": "Joint, external, or unresolved institution; review complete denominator"})
                else:
                    key = next(iter(matches))
                    ids.add(key)
                    mappings.append({"author": author["name"], "affiliation": address,
                                     "institution_id": key, "institution": institution_names[key]})
        paper = {
            "doi": row["doi"], "journal": row["journal"], "article_title": row["title"],
            "publication_date": row["publisher_date"], "journal_impact_factor": weight["impact_factor"],
            "jif_data_year": weight["jif_data_year"], "jif_verification_status": weight["verification_status"],
            "article_type": row["article_type"],
            "corresponding_authors": " | ".join(a["name"] for a in row["corresponding_authors"]),
            "corresponding_author_affiliations_json": json.dumps(row["corresponding_authors"], ensure_ascii=False),
            "normalized_affiliations_json": json.dumps(mappings, ensure_ascii=False),
            "exempted_affiliations_json": json.dumps(exempted, ensure_ascii=False),
            "evolutionary_justification": rationale, "article_url": row["article_url"],
            "relevance_review_basis": decisions.get(row["doi"], {}).get("evidence", "publisher summaries and abstracts where necessary; original NEE review"),
            "correspondence_evidence_status": row["extraction_status"],
            "correspondence_evidence_url": row.get("source_url", row["article_url"]),
            "correspondence_limitation": row.get('correspondence_limitation', ''),
            "primary_access_limitation": row.get('primary_access_limitation', ''),
            "original_research_evidence": row.get('original_research_evidence', 'primary article type and individual scientific review'),
            "publication_date_evidence": row.get("date_evidence", "publisher_article_datePublished"),
            "publication_date_source_url": row.get("publication_date_source_url") or (row.get("crossref_date_source_url", "") if row.get("date_evidence") == "publisher_deposited_online_date_via_crossref" else row.get("source_url", row["article_url"])),
            "credit_status": "pending_institution_review" if pending else "ready",
            "dataset_status": "PROVISIONAL_INCOMPLETE_SCREENING" if args.provisional else "INCOMPLETE_AUDITED_SUBSET_NOT_A_RANKING",
        }
        papers.append(paper)
        if pending:
            continue
        allocations = distribute(weight["impact_factor"], ids)
        assert sum(allocations.values(), Fraction()) == Fraction(weight["impact_factor"])
        for key, points in allocations.items():
            credits.append({**{k: paper[k] for k in ["doi", "journal", "article_title", "publication_date", "journal_impact_factor", "corresponding_authors", "corresponding_author_affiliations_json", "evolutionary_justification", "article_url", "correspondence_evidence_status", "correspondence_evidence_url", "jif_verification_status", "dataset_status"]},
                           "institution_id": key, "university": institution_names[key],
                           "eligible_arwu_top1000": str(key in universities).lower(),
                           "fraction_exact": str(Fraction(1, len(ids))),
                           "impact_factor_points_exact": str(points),
                           "impact_factor_points": format(float(points), ".10f"),
                           "credit_type": "full" if len(ids) == 1 else "fractional"})
    suffix = 'PROVISIONAL' if args.provisional else 'INCOMPLETE'
    save(f"papers_reviewed_{suffix}.csv", list(papers[0]), papers)
    if credits:
        save(f"paper_credits_{suffix}.csv", list(credits[0]), credits)
    save('unresolved_affiliations_PROVISIONAL.csv' if args.provisional else 'unresolved_affiliations.csv',
         ['doi', 'corresponding_author', 'affiliation', 'reason'], unresolved)
    print(json.dumps({"reviewed_included_papers": len(papers),
                      "papers_with_complete_institution_mapping": sum(p["credit_status"] == "ready" for p in papers),
                      "credit_rows": len(credits), "unresolved_affiliation_rows": len(unresolved),
                      "openalex_fallback_papers": len(fallback),
                      "ranking_produced": False}))


if __name__ == "__main__":
    main()
