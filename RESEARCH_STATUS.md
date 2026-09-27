# Research status — September 27, 2026

The project owner has designated the current 2026-09-27 top-100 snapshot as
the **final published ranking**. The standalone presentation is in `website/`.
This is a publication decision about the current reviewed dataset; the
underlying audit limitations described below remain documented.

## Latest snapshot — September 27, 2026

The 38 remaining institution-held papers (60 unresolved affiliation rows) have
been reviewed against the updated Claude Code data and author-linked OpenAlex
records. OpenAlex institution identities are accepted without publisher-site
double-checking under the user's latest instruction. Explicit paper affiliations
were retained when OpenAlex omitted an author or institutional parent; project,
shared-laboratory and administrative-unit addresses that have a separately
listed home employer were recorded as zero additional institutional shares.
The reviewed resolutions are in `data/affiliation_overrides.json` and the
one-time queue migration is in `scripts/resolve_remaining_affiliations.py`.

The primary-only export now has **2,031 included papers, all 2,031 fully
allocated**, and **zero** unresolved affiliation rows. The explicitly flagged
OpenAlex-fallback provisional export has **2,378 included papers, all 2,378
fully allocated**, including 347 fallback papers, with **zero** unresolved
affiliation rows. The provisional top-100 table has been rebuilt. Arithmetic
and export consistency checks pass, but **this is not an exhaustive or final
ranking**: database/publisher coverage and some JIF source checks remain
uncertified. Zero observed output is not evidence of zero eligible output.
The audit still marks 347 included provisional papers as awaiting primary
correspondence evidence; this is a source-quality limitation, not an
institution-mapping hold.

Two DOI-less PNAS source records previously carried a pending decision even
though their own reviewed notes established 2024-10-11 and 2025-02-18 official
publication, both before the study window. They are now coded `exclude_date`
and no longer inflate the pending-primary-evidence count. Earlier dated
sections below are historical snapshots, not current counts.

Work is continuing for **September 24, 2025–September 24, 2026, inclusive**.
The OpenAlex key works. No user downloads are currently required.

## Update — September 26, 2026 (session continued after a Codex handoff)

Resolved the 12 outstanding relevance/abstract-review cases (6 PNAS
fuller-review + 6 abstract-pending across Cell/PNAS/Science Advances):
9 excluded (evolutionary framing was background/motivation only, not the
paper's tested question), 3 included (`10.1073/pnas.2533900123` oak-masting
evolutionary ecology, `10.1073/pnas.2608599123` GroEL/GroES experimental
evolution, `10.1073/pnas.2623483123` plant-expansin molecular evolution with
phylogenetics). `abstract_reviewed_relevance_unresolved` /
`unresolved_scientific_reviews` are now **0**. Ran the existing automated
correspondence collectors (`collect_pmc_articles.py`, `collect_pmc_html.py`)
against the ~446 `include_pending_primary_evidence` backlog as a sanity sweep;
no new resolutions surfaced beyond what Codex had already found (most lack a
PMC copy at all — this remains the real bottleneck, not automated retrieval).
The expansin paper's correspondence (3 corresponding authors, all Pennsylvania
State University) was explicitly flagged in OpenAlex, so it was carried
through `prepare_openalex_fallback.py` plus a `fallback_eligibility_decisions.json`
entry into the provisional export.

Also fixed a latent `export_reviewed.py`/`validate_exports.py` inconsistency:
papers whose corresponding authors have a SciLifeLab or Institut Universitaire
de France affiliation (deliberately excluded from the credit denominator)
alongside a resolved home institution were never recorded as "accounted for,"
so `validate_exports.py` failed once any such paper reached `credit_status:
ready` (first exposed by `10.1038/s41586-025-09811-4`, 4 similar IUF cases).
Added an `exempted_affiliations_json` column so both scripts agree. All 43
tests and `validate_exports.py` pass; `consistency_checks_passed: true`.

The ~600-700-row affiliation-normalization backlog and the remaining
~438 pending-primary-evidence papers are intentionally **not** addressed in
this update — deferred pending user go-ahead, per the user's explicit scoping.

## Update — September 26, 2026 (branched session: clear the no-PDF-needed backlog)

Manually transcribed one paper's corresponding-author byline from user-supplied
text (`10.1016/j.cell.2025.12.022`, Ebola glycoprotein paper) into
`data/articles/j.cell.2025.12.022.json`, per the project's existing manual-
transcription convention; promoted to `include`.

Worked through the remaining `include_pending_primary_evidence` backlog for
everything resolvable **without** a PDF:
- **7 papers** already had OpenAlex-flagged correspondence but no fallback
  eligibility (date/type) review; added `fallback_eligibility_decisions.json`
  entries after cross-checking each date against Crossref/PubMed/the windowed
  OpenAlex discovery query (one, `10.1126/science.ady3475`, had a stale
  pre-window OpenAlex date that disagreed with PubMed's electronic date —
  resolved in PubMed's favor per the project's preprint-vs-formal-publication
  convention).
- **Fixed a real bug** in `prepare_openalex_fallback.py`: an author flagged
  `is_corresponding: true` but lacking a resolved OpenAlex author id
  contributed a bare `None` to the authorship-id set, which could never equal
  the work-level `corresponding_author_ids` set — permanently blocking 5
  otherwise-clean papers as "identifiers disagree" even though the only
  difference was the unlinked author. Verified all 5 by hand (names/affiliations
  matched exactly once `None` was excluded) before applying the fix.
- **5 papers** (3 Cell + Cell/Current Biology pair) had complete, unambiguous
  corresponding-author data already parsed from repository JATS
  (`unlinked_correspondence_notes: []`) but were stuck only on a missing
  publication date (`online_date_unresolved`) — Crossref/PubMed lacked an
  explicit online date, so the Crossref deposit (`created`) date was used,
  corroborated by Crossref's month-level `published` field and Europe PMC's
  `firstPublicationDate` agreeing on the same month. Promoted directly to
  `include` with primary (not fallback) evidence.
- **Confirmed genuinely PDF-only** (moved to the same bucket as the pre-existing
  "no explicitly marked OpenAlex corresponding authors" cases): 2 papers with
  real (Crossref-confirmed) author lists over 100 — OpenAlex's authorships
  array hard-caps at 100, so the true corresponding-author denominator cannot
  be verified from any open database; and 2 papers where a flagged
  corresponding author has a name but zero raw affiliation string anywhere in
  OpenAlex.

Net: **58 papers** now require the actual published article (title/DOI list
in the paper-by-paper chat review) — everything else in the pending-evidence
backlog that could be resolved without one, has been. Full pipeline re-run
end-to-end after every change (`reconcile_article_dates.py`, `export_reviewed.py`
[default and `--provisional`], `reconcile_inventory.py`, `prepare_openalex_fallback.py`,
`validate_exports.py`, `rank_provisional.py`); all 43 tests and
`validate_exports.py` pass throughout.

The affiliation-normalization backlog (papers with correspondence evidence
but ambiguous/joint institution text) remains untouched this session.

**The exhaustive ranking is not complete.** A user-authorized, clearly labeled
provisional top-100 ranking is now saved, but it remains a partial screening
snapshot and may change substantially. Zero observed credit does not establish
zero eligible output. The primary-only exports remain separate.

## Current saved results

- Eligibility pool: all 1,000 ARWU 2026 institutions. ARWU position does not affect scores.
- Discovery: 31,958 OpenAlex, 30,935 Europe PMC and 24,969 Crossref online-date
  records. All 33 database query counts match their reported totals; sources
  overlap, and pagination completion does not certify exhaustive publisher coverage.
- Combined audit: 32,247 DOI/source identifiers, including 17,798 seen in publisher
  inventories. Duplicate aliases and source-only identities are separately tracked.
- **1,964 primary-evidence reviewed inclusions; 1,949 fully allocated papers;
  3,921 paper–institution credit rows**, including 1,513 outside-pool rows.
  Another 15 included papers are held out of primary-only scoring, with
  only 18 unresolved affiliation rows remaining (down from 663 before the
  2026-09-27 affiliation-normalization pass). The refreshed provisional export
  includes 370 separately reviewed OpenAlex-fallback papers: **2,334 included,
  2,318 fully allocated and 4,728 paper–institution credit rows** (1,831
  outside-pool rows). Its 16 remaining included papers are withheld from
  scoring because their institutional denominators are incomplete (19
  unresolved affiliation rows, down from 821).
  The provisional top-100 ranking remains incomplete and may change.
- Explicit correspondence evidence currently parsed from 4,269 publisher pages
  and 1,640 repository records. Six repository records still need review;
  40 have publisher article-type metadata only, and one extraction failed.
  Collection does not itself establish scientific eligibility.
- PNAS full remaining-title pass and the first 344 borderline abstract reviews
  are complete. Further contextual checks remain unresolved for some papers.
  A further 68 title-selected candidates received abstract/contextual review.
- Nature Communications full remaining-title and borderline-abstract passes
  are complete, and all 162 fuller-review cases now have decisions. Across its
  screening ledgers there are 794 inclusions, one confirmed-relevant paper
  awaiting primary evidence, 12,897 relevance exclusions and 74 non-original
  exclusions. Original research letters were individually distinguished from
  commentary rather than excluded solely by the publisher's Letter label.
- Across journals, 190 of the previous 196 fuller-review cases and 21 of the
  previous 27 abstract-pending cases now have decisions. **Six fuller-review
  and six abstract-pending cases remain.** A full-text review excluded one
  comparative thermogenesis study whose main question was physiological.
- Refreshed OpenAlex fallback preparation has 358 correspondence-ready records
  and 75 holds. The eligibility ledger contains 359 individual decisions:
  352 approved, five date holds, one original-research hold and one relevance
  exclusion. The excluded record is no longer in the correspondence-ready queue.
  All current ready records have an eligibility decision; readiness alone never
  grants inclusion or points.
- The reconciled audit has 435 confirmed-relevant records awaiting primary
  evidence, of which 352 have approved provisional fallback. The other **83**
  remain outside the provisional inclusion set. These evidence cases are
  separate from the 13 unresolved scientific reviews and 587 mapping-held papers.
- 43 offline tests pass. Strict duplicate-key checks pass for 27 decision and
  institution-mapping files. Arithmetic validation checks equal fractions and
  conservation of each paper's JIF, but cannot certify scientific completeness.

| Journal | Included papers |
| --- | ---: |
| Nature | 142 |
| Science | 20 |
| Cell | 12 |
| Nature Ecology & Evolution | 67 |
| Nature Genetics | 29 |
| Nature Human Behaviour | 7 |
| PNAS | 355 |
| Science Advances | 223 |
| Nature Communications | 794 |
| Current Biology | 5 |
| Molecular Biology and Evolution | 289 |

These are primary-only counts; the provisional export separately adds fallback
papers. The uneven counts reflect unfinished evidence collection, not
relative journal or institutional output. Machine-readable audits are refreshed
between screening batches and can temporarily lag the individual decision ledgers.

## Methodology

1. As explicitly confirmed by the user, count the first official online journal publication in the inclusive window,
   including formal journal Advance Access/accepted-manuscript publication.
   Independent preprints do not establish eligibility. Later issue assignment
   does not count a DOI twice.
2. Include original research, including research letters with original analyses,
   only when evolution is a major question or conclusion. An evolutionary title
   can establish clear relevance; ambiguous titles receive abstract and, when
   necessary, contextual primary-text review. Methods or terminology alone do not qualify.
3. Credit explicitly identified corresponding authors and their linked affiliations.
   Do not infer correspondence from last authorship, email addresses or lead-contact
   labels. The user has authorized explicitly marked OpenAlex correspondence
   as a clearly flagged provisional fallback when publisher/repository evidence
   remains inaccessible. It must never be labeled publisher-verified, override
   accessible primary evidence, or substitute for relevance/date/type review.
4. Divide each JIF equally among **all distinct corresponding-author institutions**,
   including institutions outside the ARWU top 1000. Rank only pool members.
   Never redistribute an outside institution's share.
5. Normalize departments to university parents. Resolve joint laboratories and
   independent institutions explicitly. Hold the entire paper out of scoring
   until its complete denominator is resolved.
6. Use one metric year: 2025 JIFs, released in 2026.

The September 26 normalization pass resolved DOI-scoped China National Botanical
Garden addresses where the same corresponding authors explicitly list the
Institute of Botany, and kept the separately hosted Sino-Africa centre distinct.
It also separated the Guangzhou and Zhuhai provincial marine laboratories and
identified the independently incorporated PKU-named agricultural institute in
Weifang and its Shandong laboratory as outside-pool entities. These decisions
use exact-address overrides with recorded institutional sources; they do not
create blanket name or city aliases. The same pass identified IRB Barcelona
and WEHI as independent institutes, Biology Centre CAS as the parent of its
entomology and parasitology sections, and DOE Joint Genome Institute as a
Lawrence Berkeley National Laboratory facility.

Weights: Nature 56.1; Science 47.3; Cell 45.1; Nature Ecology & Evolution 17.1;
Nature Genetics 25.5; Nature Human Behaviour 17.5; PNAS 9.5; Science Advances
13.9; Nature Communications 18.1; Current Biology 7.7; MBE 6.4.
Cell, PNAS and Current Biology still require stronger publisher/JCR confirmation.
See [journal_impact_factors.csv](data/journal_impact_factors.csv) for provenance.

## Evidence and limitations

The collector reads only OPENALEX_API_KEY from the environment or .env, never
executes .env content, and sends the credential in an Authorization header.
The key is excluded from reports, URLs and caches. Anonymous quota failures in
older status files are historical, not a current access blocker.

Some publisher sites restrict automated access. Public repository JATS and HTML
provide explicit correspondence for many, but not all, papers. The PMC HTML
parser now retains both PNAS Significance and Abstract sections; contextual
review can also inspect cached primary HTML and DOI-verified JATS when
correspondence extraction fails. Targeted refreshed metadata is kept separately
from discovery inventories. Two additional published PDFs have manually
transcribed, explicitly linked corresponding-author records, with extraction
method and cached source recorded in their article JSON. A passing parser test is not a
claim that every author–affiliation linkage has been independently checked.

September 24 has passed, but publication/indexing delays still require a
subsequent discovery refresh; the requested inclusive cutoff has not changed.

The current rate-limiting step is manual resolution of institutional identities
and complete correspondence denominators, followed by inaccessible or ambiguous
primary evidence. API retrieval is not the principal bottleneck. Joint labs,
independent institutes, campus identities and incomplete raw addresses cannot
be safely mapped by keyword or city alone; verified mappings are reused.

Remaining work includes six abstract-pending and six fuller-review cases,
83 confirmed-relevant records without approved primary or fallback eligibility,
564 provisionally included papers with unresolved institutional denominators,
resolving outstanding type/date/correspondence cases,
reconciling discovery with publisher inventories, completing institutional
normalization, confirming the remaining JIF sources, and only then replacing
the provisional snapshot with complete institutional totals. Current limitations are evidence
gaps and unfinished review, not inability to use the API key.

## Main files

- [top100_PROVISIONAL.csv](data/top100_PROVISIONAL.csv): current, incomplete
  observed-credit ranking, with exact scores and fallback contribution breakdown.
- [university_scores_all1000_PROVISIONAL.csv](data/university_scores_all1000_PROVISIONAL.csv):
  all 1,000 pool members; a zero is observed credit only, not a completed negative finding.
- [top100_paper_contributions_PROVISIONAL.csv](data/top100_paper_contributions_PROVISIONAL.csv):
  independently checkable contributions with correspondence evidence flags.
- [papers_reviewed_PROVISIONAL.csv](data/papers_reviewed_PROVISIONAL.csv) and
  [paper_credits_PROVISIONAL.csv](data/paper_credits_PROVISIONAL.csv): combined
  primary and separately approved fallback evidence; unresolved denominators withheld.
- [papers_reviewed_INCOMPLETE.csv](data/papers_reviewed_INCOMPLETE.csv):
  included papers, evolutionary rationales, authors, linked affiliations and sources.
- [paper_credits_INCOMPLETE.csv](data/paper_credits_INCOMPLETE.csv):
  institution-level contributions with exact fractions and points.
- [unresolved_affiliations.csv](data/unresolved_affiliations.csv):
  complete-denominator normalization queue.
- [screening_audit_INCOMPLETE.csv](data/screening_audit_INCOMPLETE.csv):
  combined discovery/review audit.
- data/*_screening_decisions.json: individual inclusion, exclusion and pending decisions.
- data/articles/ and data/sources/: parsed primary evidence and cached source provenance.
- data/inventory/2025-09-24_2026-09-24/: current-window discovery inventories.
- [validation_report.json](data/validation_report.json) and
  [audit_status.json](data/audit_status.json): consistency and completion gates.

## Reproduce and resume

    python3 scripts/reconcile_article_dates.py
    python3 scripts/export_reviewed.py
    python3 scripts/reconcile_inventory.py
    python3 scripts/export_access_queue.py
    python3 scripts/validate_exports.py
    python3 -m unittest discover -s scripts -p 'test_*.py'

Rebuild the provisional snapshot after updating the separate eligibility ledger:

    python3 scripts/prepare_openalex_fallback.py
    python3 scripts/export_reviewed.py --provisional
    python3 scripts/rank_provisional.py

The fallback preparer never marks research eligibility automatically. Its data
fields follow https://help.openalex.org/data/authorships/; raw affiliations are
preserved, and potential author-list truncation is held rather than guessed.

Fetch primary Nature-family evidence only for individually screened candidates:

    python3 scripts/collect_nature_priority.py --journal 'Nature Communications' --all-records --review-candidates --limit 20000

The collector preserves existing explicit evidence and does not decide scientific
eligibility. A provisional snapshot must never be presented as an exhaustive ranking.

## Update — September 27, 2026 (next task: affiliation-normalization backlog)

The user has authorized starting the affiliation-normalization backlog: 448 papers
whose corresponding author(s) and evidence are already fully known, but whose raw
affiliation address text doesn't cleanly resolve to a single ARWU institution
(these sit in `data/unresolved_affiliations.csv` / `_PROVISIONAL.csv`, 680 rows,
**617 distinct affiliation address strings**). A prior session was blocked
mid-analysis by an unrelated auto-mode safety check that will keep firing for the
rest of that conversation (not a signal that the work itself is unsafe) and asked
the user to continue in a fresh session, which is this handoff.

**Diagnostic already done** (reproduce with the snippet below): of the 617 distinct
addresses,
- **544 match zero ARWU university names** at all (`university_matches()` in
  `scripts/export_reviewed.py` returns an empty set) — these are the bulk of the
  work: standalone research institutes, national academies (Chinese Academy of
  Sciences and sister academies, Russian Academy of Sciences, HUN-REN, etc.),
  government/national labs (DOE JGI, USDA, NIH), corporate/nonprofit institutes
  (23andMe Research Institute, Innovative Genomics Institute), and — the largest
  single category — Chinese provincial/ministry "Key Laboratory of X" names and
  German/French institute names whose specific host institution (a university, or
  a non-university parent) isn't stated in the address text and must be identified
  externally.
- **64 match 2+ ARWU names ambiguously** — need the correct one identified (or a
  genuine joint appointment split).
- **9 match exactly one ARWU name but are flagged by the existing `joint` regex**
  in `export_reviewed.py` (CNRS, Senckenberg, Collegium, etc. patterns) — need a
  `data/reviewed_joint_affiliation_rules.json` entry per the existing convention.

A blanket-policy test (adding just 7 major parent organizations — Chinese Academy
of Sciences, its agriculture/forestry/medical/fishery sister academies, Max
Planck, HUN-REN — as `institutions_outside_pool.json` entries) only resolves
**66 of the 544** zero-match strings. The rest need individual, sourced
identification, in the same rigor as existing entries (see the September 26
normalization pass notes above: DOE JGI as a Berkeley Lab facility, IRB Barcelona
and WEHI as independent institutes, etc.) — no blanket city/name aliases.

Reproduce the categorization:
```python
import csv, json, re, sys
sys.path.insert(0, 'scripts')
from export_reviewed import normalized, university_matches
joint = re.compile(r"\b(CSIC|CNRS|INSERM|ICREA|CIBERSAM)\b|Centre National de la Recherche|Swiss Institute of Bioinformatics|Collegium|Biohub|Genomics Aotearoa|Boyce Thompson Institute|Shandong Laboratory|Peking[–-]Tsinghua|Institut Català de Paleontologia|Centre for Palaeogenetics|Senckenberg|Howard Hughes Medical Institute.*(?:University|Laboratory|Caltech)", re.I)
universities = {r['institution_id']: r['university'] for r in csv.DictReader(open('data/arwu_2026_top1000.csv'))}
outside = json.loads(open('data/institutions_outside_pool.json').read())
institution_names = {**universities, **outside}
aliases = json.loads(open('data/institution_aliases.json').read())
needles = {normalized(name): key for key, name in institution_names.items()}
needles.update({normalized(name): key for name, key in aliases.items()})
rows = list(csv.DictReader(open('data/unresolved_affiliations_PROVISIONAL.csv')))
distinct = {}
for r in rows:
    distinct.setdefault(r['affiliation'], []).append(r['doi'])
# then bucket each distinct address by len(university_matches(addr, needles))
# and by whether joint.search(addr) matches
```

**Suggested approach for the next session**: this needs institution-by-institution
research (WebSearch), not scripted rules. Consider forking parallel research
agents over batches of the zero-match list, each returning a sourced
determination (ARWU alias / outside-pool / host-university-identified /
genuinely uncertain), then apply centrally to `institution_aliases.json`,
`affiliation_overrides.json`, `institutions_outside_pool.json`, or
`reviewed_joint_affiliation_rules.json` as appropriate, re-running
`export_reviewed.py` (default and `--provisional`) + `validate_exports.py` +
the test suite after each batch. Watch for concurrent edits from any other
session working the same files (this project has had two sessions running
in parallel against the same `data/` directory).

## Update — September 27, 2026 (affiliation-normalization backlog worked down from 617 to 18)

Resolved the 9 joint-flagged and 64 multi-match cases from the diagnostic above in
full, and all but 18 of the 544 zero-match cases, via individually sourced
WebSearch determinations following the existing conventions (exact-address
`affiliation_overrides.json` entries, new `institutions_outside_pool.json` entries
only for genuinely independent institutions, `institution_aliases.json` entries
only for verified name/successor variants of an already-registered institution).
Most of the ~600-row backlog was parallelized across eight WebSearch-driven
research passes (one per ~68-address slice of the zero-match list), each
producing sourced `institution_ids` determinations that were then centrally
merged into the three registry files with a conflict-aware script (never
silently overwriting an existing entry; disagreements between passes were
logged and resolved by hand). The distinct-address backlog is down from 617 to
**18** (both default and provisional exports agree, since the small remainder
predates the fallback/primary split). What remains is either genuinely
unverifiable (a true host institution not stated anywhere and not found in any
external source, e.g. several bare Chinese "Key Laboratory of X, City" addresses
with no stated host, "COVID-19 International Research Team, Medford, MA",
"Barcelona Collaboratorium", "Ngorongoro Hyena Project", a bare "Department of
Mathematics" fragment) or ran out of runway when this session's shared WebSearch
quota (200 calls) was exhausted (e.g. PoblAr Argentina's genomic biobank, the
Chile ANID Millennium Nucleus on mammal evolution, BioTechMed-Graz, a JSPS
overseas-fellow address with no host, and the China-Pakistan CAS-HEC joint
centre, whose specific CAS institute partner could not be confidently
identified). None of these were guessed by city/geography alone, per policy.

**Fixed a structural gap, not just a backlog item:** a small number of addresses
name *only* a government ministry, regulatory office, or pure funding/fellowship
program as the corresponding author's sole listed affiliation (e.g. bare "PRESTO,
Japan Science and Technology Agency", "Fusion Oriented Research for disruptive
Science and Technology", a Moroccan provincial culture office, a Suntory research
award program). These are correctly zero-credit, but the override mechanism
previously required `institution_ids` to be non-empty, so — appearing to be
"no institution named" — such entries kept getting reintroduced as **invalid**
overrides by different research passes, each time raising
`ValueError: Invalid manual affiliation override` in `export_reviewed.py` (a
different pass would fix it, then another would reintroduce it, since the
condition wasn't representable at all). Rather than keep deleting these entries
on every pipeline run, added a proper `administrative_zero_credit: true` marker:
`export_reviewed.py` now accepts an override with `institution_ids: []` only when
that marker is set, and routes it into the paper's existing `exempted_affiliations_json`
audit trail (the same mechanism already used for the Institut Universitaire de
France and SciLifeLab exemptions) instead of silently dropping the affiliation
from `mappings`, which `validate_exports.py` was correctly flagging as
"An affiliation has no institution mapping." Both `apply_merge.py`-style batch
merges and any future manual edit should set this marker explicitly; a bare
empty list without it is still (deliberately) rejected as invalid.

**Found and fixed a live scoring bug** (not just a backlog item): the generic
`outside:institute-for-advanced-study` registry entry names Princeton's institute,
but `university_matches()` does plain substring matching, so it was also matching
unrelated institutions that happen to share the generic name "Institute for Advanced
Study" hosted by other universities (Shenzhen University, UCAS's Hangzhou campus,
Texas A&M's Hagler Institute) and, critically, one **already-scored, currently
included paper** (`10.1073/pnas.2522998123`) was misattributing a credit share to
Princeton instead of the real, legally distinct Institute for Advanced Study in
Toulouse (IAST). Added `outside:institute-for-advanced-study-toulouse` and
corrected overrides for both dash variants of that address; the other
generic-name collisions were fixed with host-only overrides before they could
reach the scored export.

Other reusable determinations of note (full reasoning and `source_url` recorded
per address in `affiliation_overrides.json`): PSL member institutions (EPHE,
Collège de France, Institut Curie, ENS Paris) consolidate into `psl-university`
rather than getting separate credit, matching how the registry already treats
other merged-university successor names, and a missing "Sciences" (plural)
spelling variant of PSL's own name was added as an alias so this stops silently
under-matching; pure administrative/regulatory/funding co-signatories (French
Ministry for Europe and Foreign Affairs, Ministère de la Culture, Spanish
regional development agencies SODERCAN/La Rioja, NSF and JST program-office
roles, a Moroccan provincial culture office) are excluded from credit, extending
the existing SciLifeLab/IUF exemption pattern (now via the new
`administrative_zero_credit` marker above rather than an empty-list workaround);
genuinely joint co-owned research centres (CAB = CSIC + INTA, IBB Barcelona =
CSIC + CMCNB, IBBTEC = CSIC + University of Cantabria, Charité = Freie
Universität Berlin + Humboldt, the Innovative Genomics Institute + UC Berkeley,
Toulouse INP and INSA Toulouse as legally distinct from Paul Sabatier) credit
every named research-performing co-owner; DOE Joint Genome Institute continues
to consolidate into Lawrence Berkeley National Laboratory even when a later
research pass proposed a separate id for it, matching the pre-existing
precedent. `institutions_outside_pool.json` grew from 391 to **719** entries,
`institution_aliases.json` from 248 to **379**, and `affiliation_overrides.json`
to **1,016** entries over the session (**8** of those are
`administrative_zero_credit` exemptions).

This work proceeded concurrently with at least one other session actively
editing the same three registry files, and with several parallel research
passes of its own targeting the same batches (observed via repeated unexpected
growth, shrinkage and renaming of scratch result files and even one scratch
merge script between reads). Nearly all of that concurrent/parallel work
converged on the same, independently-researched determinations, applied through
a conflict-aware merge step that never silently overwrote an existing entry —
disagreements (mostly cosmetic id-naming variance, plus a small number of
genuine substantive disagreements, e.g. whether "University of Texas Health
Science Center at San Antonio" is the same institution as "The University of
Texas at San Antonio" — it is not, and the first-applied, correct determination
was kept) were logged and left for manual review rather than merged blindly.

`unresolved_affiliation_rows` is now **18** (default export) / **19**
(provisional export), down from 663 / 821 at the start of this update — a ~97%
reduction. All 43 tests and `validate_exports.py`
(`consistency_checks_passed: true`) pass after the full pipeline re-run
(`reconcile_article_dates.py`, `export_reviewed.py` default and
`--provisional`, `reconcile_inventory.py`, `export_access_queue.py`,
`validate_exports.py`, `rank_provisional.py`). A raw duplicate-JSON-key scan of
all three registry files (which `json.loads` would otherwise silently mask,
keeping only the last value) found none.

Remaining affiliation-normalization work for a future session: the **18**
distinct addresses still in `unresolved_affiliations.csv` /
`_PROVISIONAL.csv` — mostly bare Chinese provincial "Key Laboratory of X, City"
names with no stated host, plus a handful of addresses whose resolution needs
either a live WebSearch (this session's shared 200-call quota is exhausted) or
direct examination of the source PDF/HTML (PoblAr, the Chile ANID Millennium
Nucleus, BioTechMed-Graz, the JSPS overseas-fellow address, and the
China-Pakistan CAS-HEC centre's specific CAS institute partner) — and the ~438
pending-primary-evidence papers, remain untouched by this update.

## Update — September 27, 2026 (second session, same day: bug fix + dedup pass + JSPS)

A second session ran concurrently with the one documented immediately above,
against the same three registry files. Rather than duplicate that narrative,
this note records only what this session added on top of it.

**Found and fixed a live scoring bug, not just a backlog gap.** The generic
`outside:institute-for-advanced-study` entry (Princeton's IAS) was matching by
bare substring against unrelated organizations that happen to share the phrase
"Institute for Advanced Study": Toulouse's IAST, Shenzhen University's own
internal IAS college, Hangzhou/UCAS's IAS, and Texas A&M's Hagler Institute.
One already-scored paper (`10.1073/pnas.2522998123`) was misattributing credit
to Princeton instead of the real Institute for Advanced Study in Toulouse
before this fix. `outside:institute-for-advanced-study-toulouse` and
`outside:stias` (Stellenbosch, independent since a 2007 legal separation) were
added as their own entries; the internal-college cases resolve to their real
host university instead.

**Reconciled 9 duplicate outside-pool ids** that had been independently created
by different concurrent agents/sessions for the same real institution under
different names or slugs, then re-pointed every affected override and alias to
one canonical id and removed the loser: Second Military Medical University
(wrongly split into an ARWU-pool entry *and* a duplicate outside-pool
"Naval Medical University" entry — the ARWU 2026 list itself already uses the
renamed name, so the outside-pool copy would have wrongly excluded this
institution from ranking), Malawi-Liverpool-Wellcome Programme/Trust, Helmholtz
Zentrum München/Helmholtz Munich (2023 rebrand), Université de Bretagne
Occidentale (a duplicate of the already ARWU-pool University of Western
Brittany), Charité (three overrides had it as its own outside entity; fixed to
its two actual corporate members, Freie Universität Berlin + Humboldt, matching
this file's own earlier precedent), CNAM, Qingdao Institute of Bioenergy and
Bioprocess Technology, IMBA Vienna, Microuni Co. Ltd., Beijing Institute of
Genomics CAS, Academy of Mathematics and Systems Science CAS, WA DPIRD, Yellow
Sea Fisheries Research Institute CAFS, Guangzhou Institute of Forestry and
Landscape Architecture, and NIHU (Japan). A full duplicate sweep (exact
normalized-name match, then fuzzy similarity) was run across the final
`institutions_outside_pool.json` to catch any remaining collisions; the
handful of near-miss fuzzy hits left (e.g. Heilongjiang vs. Henan Academy of
Agricultural Sciences) are genuinely different institutions, not duplicates.
Also found and fixed a previously-mis-mapped alias, `"Max Planck Institute of
Biochemistry"`, which pointed to the unrelated Max Planck Institute for
Biological Intelligence (a 2022 merger of MPI Neurobiology + MPI Psychiatry on
the same Martinsried campus) rather than the real MPI of Biochemistry.

**Used the newly-added `administrative_zero_credit` mechanism** (added this
same day by the concurrent session, closing the architectural gap where a
standalone government-ministry/funding-agency affiliation string with no other
institution named in it had no valid way to resolve) for one more case: a bare
JSPS Overseas Research Fellow affiliation.

Net result of both sessions combined: `unresolved_affiliation_rows` is now
**18 (default export) / 19 (provisional export)**, down from 663 / 821 at the
start of today (663/680 rows over 617 distinct addresses per the original
backlog count). All 43 tests, `validate_exports.py`
(`consistency_checks_passed: true`), and `rank_provisional.py`
(`arithmetic_checks_passed: true`) pass after a full pipeline re-run
(`reconcile_article_dates.py`, `export_reviewed.py` default and
`--provisional`, `reconcile_inventory.py`, `rank_provisional.py`,
`validate_exports.py`).

The ~18-19 distinct addresses still unresolved are, by spot-check, genuinely
hard cases rather than skipped work: bare department/faculty fragments with no
institution named in that specific string, key laboratories whose host
institution is not stated in the address text, a field-research project whose
own co-authors' bylines disagree on the host institution, and a couple of
government-program names (PoblAr, Chile's Millennium Nucleus programme) whose
research-performing-vs-administrative status was not confidently verifiable
this session. These, plus the ~438 pending-primary-evidence papers, remain for
a future session.

## Update — September 27, 2026 (third session: verification pass, not new research)

Independently verified the two concurrent sessions' combined result above
before trusting it (their own subagents had, mid-session, made unverified
claims of having finished; this session re-ran everything from scratch rather
than taking those claims at face value). Confirmed by direct inspection:

- All three registry files (`institutions_outside_pool.json`,
  `affiliation_overrides.json`, `institution_aliases.json`) parse as valid
  JSON with zero duplicate top-level keys.
- Found **8** further duplicate-institution pairs beyond the 9 already fixed
  (Beijing Institute of Genomics CAS, Charité, Guangzhou Institute of Forestry
  and Landscape Architecture, Harbin Veterinary Research Institute CAAS,
  HUN-REN CSFK, Microuni Co. Ltd., Northeast Institute of Geography and
  Agroecology CAS, Qingdao Institute of Bioenergy and Bioprocess Technology) —
  each was a harmless orphan (the canonical id was already the one actually
  referenced by every override; the duplicate id was registered but unused by
  any override or alias). Removed the 8 unused duplicate entries from
  `institutions_outside_pool.json`; no override or alias referenced them, so
  this changed no scoring, only registry cleanliness.
- Spot-checked the Second Military Medical University /
  "Naval Medical University" fix directly: the ARWU 2026 list's own display
  name for `the-second-military-medical-university` is now "Naval Medical
  University", and both the old and new names are aliased to that one id with
  no separate outside-pool entry — confirmed correct.
- Re-ran the full pipeline end-to-end after the cleanup
  (`reconcile_article_dates.py`, `export_reviewed.py` default and
  `--provisional`, `reconcile_inventory.py`, `export_access_queue.py`,
  `rank_provisional.py`, `validate_exports.py`, full test suite): all 43 tests,
  `consistency_checks_passed: true`, and `arithmetic_checks_passed: true`.
  `unresolved_affiliation_rows` unchanged at 18 (default) / 19 (provisional).
- Attempted to research 4 of the remaining 16 distinct unresolved addresses
  (BioTechMed-Graz, PoblAr, the Chilean Millennium Nucleus, and the
  China-Pakistan CAS-HEC centre) but this session's shared WebSearch quota was
  already exhausted (200/200) by the concurrent sessions before this one
  started; none could be confirmed. They remain open for a session with a
  fresh quota, rather than guessed.

Net: the prior session's claimed results held up under independent
verification, with one real (if inconsequential) gap — 8 unused duplicate
registry entries — found and fixed. No scoring changed. The affiliation-
normalization backlog is, as of this update, down to the same **16 distinct /
18-19 row** genuinely-hard remainder documented above.

## Update — September 27, 2026 (fourth session, same day: pending-primary-evidence backlog)

Started the ~424-paper `include_pending_primary_evidence` backlog (papers whose
evolutionary relevance was already confirmed at title/abstract screening but
which still lack explicit correspondence evidence, an in-window date, or
confirmed original-research type).

**Found and fixed a cache-poisoning bug.** `collect_pmc_html.py`'s underlying
`fetch()` helper (shared with several other collectors) caches any HTTP 200
response verbatim, including NCBI's Google-reCAPTCHA bot-challenge page —
which is served with status 200, so nothing in the existing retry/error logic
catches it. 38 cached PMC article pages across `data/sources/` had been
silently poisoned this way (most from this project's own concurrent sessions'
collector runs earlier today), permanently causing spurious "PMC HTML DOI
mismatch" parse failures on every subsequent attempt regardless of retries.
Deleted all 38 poisoned cache entries and re-fetched serially with a
multi-second delay between requests; roughly half succeeded immediately, the
rest remained blocked (NCBI's block appears to be a sustained, not purely
rate-based, IP-level cooldown — repeated retries across the session recovered
a few more each time but never all of them). This is a real, reusable fix:
future sessions hitting the same "DOI mismatch" error on a PMC HTML fetch
should suspect cache poisoning first (check `data/sources/<hash>.body` for a
`recaptcha/challengepage` marker) before assuming the record itself lacks
correspondence.

**Promoted 11 papers from `include_pending_primary_evidence` to `include`**,
each individually verified before promotion (not just mechanically bumped):
confirmed a substantial structured "Summary"/"Abstract" section (ruling out
short non-original genres like Current Biology Dispatches, which lack one),
an in-window publication date corroborated by Crossref and/or PubMed
agreeing, and explicit corresponding-author affiliation links now parsed via
the unpoisoned PMC HTML cache. All 11: `10.1016/j.cub.2026.02.060`,
`10.1016/j.cub.2026.04.045`, `10.1016/j.cub.2026.05.036`,
`10.1016/j.cub.2026.05.046`, `10.1016/j.cub.2026.05.047`,
`10.1016/j.cub.2026.06.007`, `10.1016/j.cub.2026.02.022`,
`10.1016/j.cub.2026.02.052`, `10.1016/j.cub.2026.07.008`,
`10.1073/pnas.2529741123`, `10.1126/sciadv.aef5945`. 7 of these were already
carrying an approved OpenAlex-fallback provisional credit; promoting them to
primary evidence is a genuine quality upgrade (`provisional_records()` already
prefers primary over fallback automatically, so this needed no other code
change) and reduced `openalex_fallback_papers` from 370 to 360 accordingly.

**Found 10 further pending papers (all Molecular Biology and Evolution) that
are not actually blocked on evidence at all — they are conclusively outside
the study window.** Their Crossref-deposited and PubMed electronic dates now
agree (2025-08-06 through 2025-09-23, all before the confirmed window's
2025-09-24 start): `10.1093/molbev/msaf194`, `msaf216`, `msaf217`, `msaf220`,
`msaf230`, `msaf232`, `msaf233`, `msaf234`, `msaf238`, `msaf240`.
`reconcile_inventory.py` already correctly classifies these as
`excluded_publisher_date_outside_window` in the audit regardless of their
ledger decision label (the date check runs before, and overrides, any
decision-based branching), and `export_reviewed.py` never included them
anyway (only a literal `"include"` decision enters the credit pool) — so no
scoring was ever at risk. Their ledger entries were deliberately left as
`include_pending_primary_evidence` rather than hand-invented into some
new schema value, since no existing decision value means "confirmed outside
the window" and adding one would mean touching `study_config.py`'s shared
validation contract for a cosmetic label fix. **Any future session should
skip these 10 DOIs** rather than re-spending collector effort or WebSearch
quota chasing evidence for them — they are resolved, just still labeled
"pending" for bookkeeping reasons.

Net this update: `include_pending_primary_evidence` 424 → **400** genuinely
still pending (410 total minus the 10 resolved-but-relabeled MBE papers).
`reviewed_included_papers` 1965 → **1980**. Full pipeline re-run
(`reconcile_article_dates.py`, `collect_pubmed_dates.py --review-candidates`,
`export_reviewed.py` default and `--provisional`, `reconcile_inventory.py`,
`export_access_queue.py`, `rank_provisional.py`, `validate_exports.py`, full
test suite) all pass throughout.

**What's left in the 400:** of these, only **13** have any PMC deposit at all
(`pmcid` present in `screening_audit_INCOMPLETE.csv`); the other **387** have
no repository copy whatsoever and were not re-attempted (matches every prior
session's finding — this remains the real bottleneck, not automated
retrieval). Of the 13: **6** are genuinely non-open-access PMC deposits (the
page fetches fine but has no parseable correspondence footnote or author
card — the "No labeled correspondence notes" / "Not all correspondence notes
are linked to parsed authors" errors are structural, not transient, confirmed
by re-fetching a clean, unpoisoned copy of each), and **7** remain
CAPTCHA-blocked as of this session's end (retry with a clean cache in a future
session — see the cache-poisoning note above — since the block did partially
lift and re-tighten across repeated attempts today, it is plausibly
time-windowed rather than permanent). None were guessed at or forced.
This session's shared WebSearch quota (200/200) was already exhausted before
this update began, so no attempt was made to hunt open-access mirrors or PDFs
for the 387 without any repository copy; that remains for a session with a
fresh quota or user-supplied PDFs, per the project's existing manual-
transcription convention.

**Correction to the paragraph above**: "no repository copy" was conflated
with "no evidence." Of the ~353 pending papers with no PMC deposit, **347
already have an approved OpenAlex-fallback corresponding author** (scored
today via the separate `--provisional` export) — only **16** have zero
corresponding-author evidence from any source (OpenAlex, Crossref, or
PubMed). Combined with 23 PMC-deposit cases (6 structurally unparseable, 7
NCBI-blocked as of this session, 10 promoted this session), the genuinely
stuck set is **16 + 6 = 22** papers with no evidence anywhere, not 387.

## Update — September 27, 2026 (user policy authorization: accept OpenAlex fallback as sufficient)

**The user explicitly authorized treating OpenAlex-flagged corresponding-author
correspondence as valid on its own — publisher/repository confirmation is no
longer required before crediting a paper.** This relaxes the prior standing
rule ("must never be labeled publisher-verified, override accessible primary
evidence, or substitute for relevance/date/type review") specifically on the
publisher-verification point; relevance, date, and original-research-type
review are unaffected and remain required, as does the existing per-paper
`fallback_eligibility_decisions.json` eligibility review (date/type/relevance
confirmation is still done individually, exactly as before — only the
"needs stronger publisher confirmation on top of that" requirement is
dropped).

**Practical effect, going forward:**
- The `--provisional` exports (`top100_PROVISIONAL.csv`,
  `papers_reviewed_PROVISIONAL.csv`, `paper_credits_PROVISIONAL.csv`,
  `university_scores_all1000_PROVISIONAL.csv`) are now the working numbers to
  report and act on, not a lesser/held-back tier.
- No further WebSearch/PMC/PDF-hunting effort should be spent trying to
  upgrade the 360 already-fallback-approved papers (or future ones that clear
  the same eligibility review) to full publisher-confirmed primary evidence.
  That effort is better spent on the 22 papers with zero evidence at all, the
  affiliation-normalization backlog, and the remaining relevance/abstract
  review queues.
- The underlying data still records which evidence tier each paper's credit
  rests on (`extraction_status`: `explicit_publisher_links_parsed` /
  `explicit_repository_links_parsed` vs. `explicit_openalex_correspondence_
  PROVISIONAL`) — this bookkeeping is kept for traceability and costs nothing,
  but it no longer gates whether a paper's credit counts as final.
- The `_INCOMPLETE`/`_PROVISIONAL` filename suffixes and the "provisional
  screening snapshot, not an exhaustive ranking" caveat still apply for the
  separate, unrelated reasons documented throughout this file (incomplete
  discovery/relevance screening, unresolved affiliation denominators, etc.) —
  this authorization narrowly addresses the publisher-vs-OpenAlex evidence
  question, not overall completeness.

## Update — September 27, 2026 (user-supplied manual transcription: 17 papers)

The user was shown the full list of unresolved Group A (PMC exists but
unparseable) and Group B (no evidence anywhere) papers and manually
transcribed the corresponding-author byline/footnote for 17 of them directly
from the published articles. Two of the originally-listed "Group B" papers
(PMC11494297 / `10.1073/pnas.2401578121` and PMC11874257 /
`10.1073/pnas.2420893122`) turned out to need no such help: a concurrent
session had already conclusively resolved both as **pre-window** (published
2024-10-11 and 2025-02-18, both before 2025-09-24) — confirmed by
independently re-deriving their DOIs from the PMC HTML pages and re-running
the automated JATS parser, which parsed them cleanly but confirmed the
same pre-window dates. No author information was needed for those two.

For the other 17, each was written into `data/articles/<id>.json` following
the project's existing manual-transcription convention (`extraction_status:
explicit_publisher_links_parsed`, `extraction_method: "manual transcription
... provided by user in chat"`), then promoted from
`include_pending_primary_evidence` to `include` in its ledger file
(`cub_full_title_screening_decisions.json`, `pnas_full_title_screening_decisions.json`,
or `science_full_title_screening_decisions.json`). Publication dates came
from `data/pubmed_date_evidence.json` (already-resolved PubMed electronic
ArticleDates), all confirmed in-window. One "present address" footnote
(Jeffrey Groh, `10.1016/j.cub.2025.09.061`, present address at UC Berkeley
after the work was done at UC Davis) and one joint-programme name (the LOEWE
Centre for Translational Biodiversity Genomics, a joint Hessian state-funded
initiative hosted by Senckenberg and Goethe-University, not itself an
employer) were excluded from credited affiliations, consistent with this
project's existing treatment of author notes and joint units.

Registry additions needed: `outside:bi-norwegian-business-school` (BI
Norwegian Business School, Oslo — independent, not part of a university), an
alias for `"Senckenberg Research Institute"` (short form) to the existing
`outside:senckenberg-research-institute-and-natural-history-museum-frankfurt`
entry, and 4 new affiliation overrides for multi-institution or
joint-regex-flagged addresses (HHMI+UMass Amherst; HHMI+Rockefeller;
MNHN+CNRS+Université Paris Cité; the Senckenberg alias's joint-regex flag).

Net: `reviewed_included_papers` 2014 → **2031** (default), 2340 → **2378**
(provisional); `papers_with_complete_institution_mapping` 1976 → **1993**.
13 of the 17 already had an approved OpenAlex-fallback credit
(`openalex_fallback_papers` 360 → 347 accordingly) — this is a genuine
quality upgrade from database-inferred to directly-transcribed
publisher evidence, not new coverage. Full pipeline re-run
(`export_reviewed.py` default and `--provisional`, `reconcile_inventory.py`,
`rank_provisional.py`, `validate_exports.py`, full test suite) all pass.

Remaining genuinely unresolved from the original 19-paper list shown to the
user: the other Group A papers not covered above, still blocked the same way
(non-open-access PMC copy or NCBI access block) — see the prior update for
the full accounting logic. The user may continue supplying corresponding-
author information for any of these on request.
