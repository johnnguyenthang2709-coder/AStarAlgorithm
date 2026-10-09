# Springer LNCS report

**Title:** A* Search for Road Routing and Partially Observed Robot Navigation: Design, Implementation, and Experimental Evaluation.

This complete manuscript describes the frozen implementation and its actual experiments. Entry point: `main.tex`; compiled artifact: `report.pdf`. Nine sections, eight report figures, three tables, one implementation-faithful algorithm, and nine substantively cited references. Bibliography: `references.bib`. Additional supplied literature: `LITERATURE-REVIEW-MATRIX.md` and `literature-inventory.json` (all eight PDFs, seven unique studies).

## Provenance and protected baseline

- Reporting branch: `codex/springer-lncs-report`, created directly from `04c48468c6b6b4f6512be925383614267fa7ca32` on `codex/academic-benchmark-final`.
- Scientific-writing revision: `codex/springer-lncs-writing-refinement`, based on completed report commit `861e120`. See `WRITING-STYLE-REVIEW.md` for scope and before/after assessment.
- Authors' original checkout: `D:/Project/AStarAlgorithm-authors-benchmark`, clean at Git commit `8bbbfb81cbe76c9f559f15f5c68f1eb4998915d8`.
- No production, sensing, navigation, historical result, source-map, or benchmark file is changed. No merge or hosting action is performed.
- Figures are redrawn at LNCS width from committed raw data; original plots and measurements remain unchanged. The map figure calls the existing RoadEngine only to recover three fixed routes and checks recorded costs. The robot figure reads frozen sightings and paths, never hidden polygons.
- The supplementary papers are user-provided untracked inputs; they remain in `reference/Papers` and are not redistributed in the report commit.

## Official format

`llncs.cls` and `splncs04.bst` are unmodified official Springer files from the CTAN LNCS distribution, class **v2.26 (25-Feb-2025)**. Source: <https://mirrors.ctan.org/macros/latex/contrib/llncs.zip>. The upstream README identifies copyright Springer and CC BY 4.0-or-later distribution. Attribution is retained in the files and `template/UPSTREAM-README.md`; official class documentation source is in `template/llncsdoc.tex`.

The official publisher example `template/samplepaper.tex` was downloaded through [Springer's author page](https://link.springer.com/series/558/information-for-authors-and-editors) on 2026-10-09. That downloadable bundle labels its example/class v2.25 (03-Sep-2026), whereas the installed/CTAN distribution is v2.26 (2025). Both origins are recorded; we use the consistent unmodified CTAN class/style pair, not a hybrid or imitation. The example is retained for reference, not included in the manuscript. `template/provenance.json` records checksums and URLs.

Single column, default class text area and fonts, numbered references with `splncs04`; no geometry, font-size compression, negative spacing, manual page-filling, or IEEE formatting. Natural-bottom alignment (`raggedbottom`) prevents stretched paragraph gaps around floats. Standard class option `orivec` (passed before the explicit `documentclass[runningheads]{llncs}`) resolves the documented bold-vector/amsmath conflict; the report does not use vector accents. Neither choice changes fonts or margins.

## Submission metadata

`metadata.tex` intentionally contains **Author name to be supplied** and **Affiliation to be supplied**. These are explicit unverified metadata fields, not fabricated identities or inferred institutional affiliation. Replace them with approved author, running author, and affiliation before submitting. No email, ORCID, course, or coauthor is invented. The body is complete despite those configurable metadata fields.

## Build and validate

From repository root, in this Windows environment:

```powershell
py -3.14 report/springer-lncs/scripts/make_figures.py
& report/springer-lncs/scripts/build.ps1
py -3.14 report/springer-lncs/scripts/validate_report.py
py -3.14 report/springer-lncs/scripts/validate_pdf_text.py
py -3.14 report/springer-lncs/scripts/render_qa.py
```

`build.ps1` runs pdfLaTeX, BibTeX, then two pdfLaTeX passes with `-jobname=report`, failing on compilation errors or final warnings. Pass `-TexBin` to select another MiKTeX directory. With a Unix TeX installation, run the equivalent `pdflatex -interaction=nonstopmode -halt-on-error -jobname=report main.tex`, `bibtex report`, and two further LaTeX passes from this directory. Class/style and final figures are included, so a manuscript build needs no figure regeneration or original research checkout.

Figure regeneration requires Python with Matplotlib, Shapely, and the unchanged project Python 3.12 C++ binding. QA requires pypdf, Pillow, and Poppler `pdftoppm`. The provided workflow used system Python 3.14, Matplotlib 3.10.8, Shapely 2.1.2, pypdf 6.10.2, and MiKTeX pdfTeX 1.40.28. These are report-generation dependencies, separate from historical measurement runtimes.

For searchable ligatures, install **CM-Super** and enable its standard TeX font maps (MiKTeX package `cm-super`, or the equivalent TeX Live package). The preamble enables `glyphtounicode` and `pdfgentounicode=1`; these map glyphs without changing the LNCS font family or sizes. `validate_pdf_text.py` rejects Type 3 fonts, missing Unicode maps, replacement/control characters, or broken representative search terms, checking both pypdf and Poppler. A report build needs these checks as well as successful compilation.

`validate_report.py` verifies all frozen final-manifest hashes, independently recomputes principal paired statistics, checks citation coverage, sections, abstract length, page size, and final log. It calls the existing read-only benchmark consistency validator. It writes only report-local `validation.json`. `render_qa.py` writes ignored page images and contact sheets. `SCIENTIFIC-QA.md` and `LAYOUT-QA.md` record the evidence and completed review.

## Interpretation to preserve

- Road: equal graph-optimal costs on 180 queries; 76.0% median paired expansion reduction, 0.338 time ratio; seven unfavorable timing pairs retained.
- Robot: 21 local requests from 351 decisions, equal observed information but different graph representations; not a complete online navigation comparison or paper-table reproduction.
- Point interior-only and strict boundary conventions remain separate; radius-0.5 clearance is diagnostic only.
- A*-computed observed-parent return and verified reverse-entry fallback are different mechanisms. The conditional bound concerns executed geometric length.
- The 48-configuration end-to-end matrix remains unexecuted under the validity gate; no superiority claim is made.
- Road batches record mean time per call, followed by median across seven batches. Robot timings use median of 31 calls after three warm-ups. No core-only robot speedup is claimed.

For rerunning experiments rather than rebuilding the manuscript, use the original commands in `experiments/benchmarks/FINAL-BENCHMARK-REPORT.md` and cohort reports **in a separate experimental checkout/output location**. Their capture/timing scripts may rewrite historical artifacts; the reporting workflow deliberately does not execute them.
