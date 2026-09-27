"""Shared scope and narrowly scoped credential loading."""
import json
import os
from pathlib import Path
import shlex

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "data/study_config.json").read_text())
START = CONFIG["publication_start"]
END = CONFIG["publication_end"]
INVENTORY = ROOT / "data/inventory" / f"{START}_{END}"


def screening_key(key):
    if key.startswith(("10.", "PMC:", "MED:", "https://openalex.org/")):
        return key
    if key.startswith("s") and "/" not in key and key:
        return "10.1038/" + key
    raise ValueError("Unrecognized screening record identifier")


def screening_decisions():
    decisions = {}
    for path in sorted((ROOT / "data").glob("*_screening_decisions.json")):
        for key, decision in json.loads(path.read_text()).items():
            doi = screening_key(key)
            if doi in decisions:
                raise ValueError("Conflicting review ledgers for " + doi)
            if decision.get("decision") not in {"include", "exclude_relevance", "exclude_document_type", "exclude_date", "needs_abstract_review", "needs_fuller_relevance_review", "include_pending_primary_evidence", "include_pending_date_policy"}:
                raise ValueError("Unknown screening decision for " + doi)
            decisions[doi] = decision
    return decisions


def load_openalex_key(path=None):
    """Read only OPENALEX_API_KEY; never execute or interpolate .env content."""
    existing = os.environ.get("OPENALEX_API_KEY", "").strip()
    if existing:
        return existing
    path = Path(path) if path is not None else ROOT / ".env"
    if not path.exists():
        return None
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if line.startswith("export "):
            line = line[7:].lstrip()
        name, separator, value = line.partition("=")
        if separator and name.strip() == "OPENALEX_API_KEY":
            try:
                parts = shlex.split(value, comments=True, posix=True)
            except ValueError:
                raise ValueError("OPENALEX_API_KEY has invalid quoting in .env") from None
            if len(parts) != 1 or not parts[0]:
                raise ValueError("OPENALEX_API_KEY must contain one nonempty value")
            os.environ["OPENALEX_API_KEY"] = parts[0]
            return parts[0]
    return None


def openalex_headers():
    key = load_openalex_key()
    return {"Authorization": "Bearer " + key} if key else {}
