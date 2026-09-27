Let's generate a ranking of evolutionary biology research at the top 100 universities worldwide.

The ranking should include only original research papers published in evolutionary biology and should be based solely on the summed journal impact factors of qualifying publications from each university between September 24, 2025 and September 24, 2026, inclusive (publication window updated by the user on September 24, 2026).

Use publications from the following journals:

Nature
Science
Cell
Nature Ecology & Evolution
Nature Genetics
Nature Human Behavior
Proceedings of the National Academy of Sciences (PNAS)
Science Advances
Nature Communications
Current Biology
Molecular Biology and Evolution

For papers published in broad-scope journals such as Nature, Science, Cell, PNAS, Science Advances, Nature Communications, and Current Biology, include a paper only if its primary scientific contribution is clearly related to evolutionary biology. Relevant topics include, but are not limited to, evolutionary genetics, population genetics, molecular evolution, phylogenetics, comparative genomics, speciation, adaptation, natural or sexual selection, experimental evolution, evolutionary ecology, quantitative genetics, paleogenomics, human evolution, host–pathogen coevolution, genome evolution, and the evolution of development.

Use the journal impact factor as the weight of each qualifying paper. Use one consistent set of Journal Impact Factors for all journals, preferably the most recent Journal Citation Reports values available in 2026. Clearly report the impact factor used for each journal.

Only corresponding-author affiliations should receive credit. Do not assign credit based on first-author or other non-corresponding-author affiliations.

Credits should be assigned to universities or equivalent research institutions, not to individual departments, institutes, laboratories, or programs within a university. Normalize different names referring to the same university into a single institution.

If a paper has one corresponding author affiliated with one university, that university receives the full journal impact factor.

If there are multiple corresponding authors associated with different universities, divide the journal impact factor equally among the distinct corresponding-author universities. For example, if a paper in a journal with an impact factor of 20 has corresponding authors from two universities, each university receives 10 points. If three universities are represented among the corresponding authors, each receives 20/3 points.

If several corresponding authors are affiliated with the same university, count that university only once when dividing the credit. If a corresponding author lists multiple university affiliations, count each qualifying university affiliation and divide the credit accordingly among all distinct corresponding-author universities.

As confirmed by the user, retain all distinct corresponding-author institutions in the denominator, including institutions outside the ARWU top 1000. Only ARWU top-1000 institutions enter the final ranking; outside-pool shares must not be redistributed to pool members.

Search all universities included in the top 1000 of the latest available Academic Ranking of World Universities (ARWU). The ARWU list is used only to define the pool of institutions to examine and should not otherwise influence the ranking.

Search the official websites of the journals listed above to identify all relevant papers published within the confirmed date window and obtain the article title, publication information, corresponding-author information, and affiliations. Whenever the evolutionary-biology relevance of a paper in a multidisciplinary journal is unclear, examine the abstract and article information. If necessary, use PubMed, bioRxiv, or the article itself to determine whether the paper should be classified as evolutionary biology. OpenAlex is also authorized as a supplementary metadata source. Do not classify a paper as evolutionary biology merely because it uses genomic, ecological, or computational methods; evolution must be a major scientific question or conclusion of the study.

Include research articles and research letters where they report original research. Exclude reviews, perspectives, commentaries, editorials, news articles, corrections, book reviews, protocols, and other non-original-research content.

For every qualifying paper, record:

Journal
Article title
Publication date
Journal impact factor
Corresponding author(s)
Corresponding-author affiliation(s)
University or institution receiving credit
Fraction of the impact factor assigned to each institution
Impact-factor points assigned to each institution
Brief justification for classification as evolutionary biology when the classification is not obvious

Save the collected data in a csv file.

After collecting all qualifying papers, sum the impact-factor credits for every institution.

Examine all institutions in the ARWU top 1000 rather than stopping after enough universities have been found to construct a top 100.

Finally, rank universities from highest to lowest according to their total accumulated impact-factor score and report the top 100.

For each of the top 100 universities, report:

Rank
University
Total impact-factor score
Number of qualifying papers
Number of full-credit and fractional-credit papers

Also provide a supplementary paper-level table showing every publication contributing to each university's score so that the ranking can be independently checked.

This is a custom bibliometric ranking defined by these rules. Do not introduce citation counts, publication counts, faculty size, h-index, reputation, existing university rankings, departmental strength, or any other metric into the ranking. Follow the methodology above strictly.

## Published website and repository data

The project owner designated the current reviewed top-100 snapshot as the
final published ranking. Open [website/index.html](website/index.html) in a
browser to view the mobile-friendly English/Chinese site. Its standalone
`website/assets/` folder contains separate ranking and paper data files, plus
CSV downloads. The included-paper CSV contains all 2,378 qualifying papers;
the website's Papers tab lets visitors search and filter that full list.
To rebuild those assets from the reviewed exports, run:

```bash
python3 scripts/build_ranking_website.py
```

Only a compact final dataset and its mapping/provenance tables under `data/`
are staged for GitHub. Intermediate article JSON, review ledgers, screening
audits and downloaded API/page caches remain available locally but are excluded
by `.gitignore`; reproducing the *entire collection process* from a fresh clone
would require those local archives or re-collection. The tracked final exports
are sufficient to rebuild the website and independently inspect the published
scores and paper-level credits. The private `.env` API key is excluded; never
force-add it to Git.

Before pushing, review `git status` and `git diff --cached --stat` and confirm
that `.env` and the excluded intermediate directories are absent from the
staged files.
