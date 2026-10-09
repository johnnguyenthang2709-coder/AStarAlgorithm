# Conversion and quality assurance

## Provenance and scientific equivalence

- Authoritative source: LNCS revision `faaeb2c`; metadata revision `de4d1ed`, editorial revision `6a48eaa` inherited.
- Dedicated conversion branch: `codex/hcmut-project-report`.
- All 53 tracked source-manuscript files match their original Git blobs, including the original PDF, bibliography, metadata, Unicode configuration, and figures. Windows checkout line endings are handled through Git's normal filters.
- All nine source section bodies appear in the converted sources in their original sequence, ignoring whitespace and float-placement options. The only additions are report organization, an accessible interface explanation, and qualified future improvements. Adapted primary headings follow the university brief.
- Abstract, five displayed equations, implementation-faithful algorithm, and literature synthesis remain intact. The supplementary matrix covers eight accessible PDFs representing seven unique studies and is copied unchanged.
- Eight figure PDFs are byte-identical; three tables retain every caption, label, row, and value. Nine BibTeX entries and the numeric bibliography style are byte-identical.
- 56 manifest hashes remain equal to the frozen benchmark. Existing independent benchmark consistency checks pass for 180 road pairs, 351 captured robot states, and 21 eligible local comparisons.
- No new experiments, production changes, altered collision assumptions, or claims of unknown-world optimality were introduced. The blocked 48-case comparison remains blocked and unexecuted.

## Format and navigation

The final document has **22 physical A4 pages**: cover (no printed number), abstract (i), contents (ii), and 19 Arabic-numbered body/reference pages. Introduction is physical page 4 with printed page 1. Contents is generated automatically, fits one page, and all numbered section/subsection destinations are checked against extracted page text. References now occupy printed page 19 (physical page 22) together.

The format check confirms `article[a4paper,12pt,oneside]`, a 160 mm x 247 mm text area (2.5 cm margins), one column, and 1.15 body line spacing. The contents page uses ordinary single spacing without reducing font size. The three nested cover rectangles are confined to the cover. Institution names, report topic, subtitle, lecturer, and five-student table remain within the frame. The cover uses the author's supplied logo, Faculty of Applied Science, and lecturer Phan Thanh An. The PNG is unchanged and proportionally rendered at 12 cm width, including its original white margins. Border insets and line weights follow the supplied LaTeX template. The five supplied Vietnamese names, class CC06, and student IDs are printed without inferred emails or submission date.

## Build and extraction

Commands actually executed from the repository root:

```powershell
& report/hcmut-project/scripts/build.ps1
py -3.14 report/hcmut-project/scripts/validate_report.py
py -3.14 report/hcmut-project/scripts/render_qa.py
py -3.14 report/springer-lncs/scripts/validate_report.py
git diff --exit-code -- report/springer-lncs
pdffonts report/hcmut-project/report.pdf
git diff --check
```

The final pdfLaTeX/BibTeX build has no overfull/underfull boxes, unresolved references, font substitutions, duplicate destinations, or LaTeX/package warnings. Initial diagnostics found a cover font substitution and duplicate page anchor; both were resolved in the new project only. A preliminary contents page orphaned its final entry; ordinary single spacing resolved it. No font or margin shrinkage was used.

pypdf and Poppler both extract searchable Unicode, including accented names and mathematical symbols, without replacement/control characters. `pdffonts` confirms embedded fonts and Unicode maps, with no Type 3 resources. Kerning may cause extractor-dependent spaces inside uppercase cover words; visual text and glyph mappings are correct. Text extraction is not a structured mathematical export.

## Complete visual inspection

All 22 final pages were rendered at 120 dpi and inspected using labeled contact sheets, with full-size checks of the cover, contents, algorithm, quantitative tables, equations, and references. No clipping, overlapping elements, unreadable captions, distorted figures, or unintended blank pages were observed. Dedicated float pages use compact top alignment rather than large distributed gaps. Body text and captions remain within the intended single-column area.

The cover now follows the supplied source LaTeX template, adapted to the A* topic, lecturer Phan Thanh An, Faculty of Applied Science, and verified five-student list. The sample Calculus title, lecturer, email list, group, and date are not reused. The separate LNCS author metadata and affiliation remain unchanged.

## Previous cover revision validation (commit 597db50)

The cover-only revision is rebuilt using the commands above (the independent HCMUT validator verifies the unchanged LNCS source blobs). Both pypdf and Poppler extraction check all five accented names, class CC06, and student IDs. All 21 pages after the cover have identical extracted text and pixel-identical 120 dpi renders compared with the preceding PDF. The complete rebuilt PDF is rendered for layout checks; cover fonts must be embedded with Unicode maps and no Type 3 glyphs.

## Final layout refinement

See `FINAL-LAYOUT-REVIEW.md` for the final 22-page placement audit. The centered cover, every rendered page, coherent road-results page, unchanged figure sizes, and final single-page bibliography were reviewed. Source and benchmark validators pass. The earlier pixel-identical body-page comparison applies to the previous cover-only revision; the current revision intentionally changes body pagination while preserving scientific text.

## Cover wording and typography update

The cover now uses the supplied Vietnam National University Ho Chi Minh City / Ho Chi Minh City University of Technology hierarchy, retaining FACULTY OF APPLIED SCIENCE. All three topic components use bold uppercase at the same size, and the logo width is reduced from 12 cm to 10.5 cm. The rebuilt cover was visually inspected; all five title lines share the same embedded font and size. All 21 subsequent pages retain identical extracted text and PDF drawing commands compared with the preceding layout revision. Build and report validators pass; the report remains 22 pages.

## Comprehensive final pagination audit

The current review supersedes the preceding placement review: see `FINAL-LAYOUT-QA.md` and `assets/layout-overview.png`. All 22 pages and consecutive transitions were inspected after the final pdfLaTeX build. Scientific content and frozen artifacts pass preservation checks. The approved cover retains PROJECT REPORT CALCULUS 1 and FACULTY OF APPLIED SCIENCE; it is pixel-identical to the pre-audit working-tree cover. The older initial-conversion course/figure-size statements above are historical, not the current specification.

## Continuous section flow correction

All body-section/subsection page reservations and float barriers removed per user instruction. Sections 1–9 follow natural article pagination. Rebuilt PDF: 22 pages; build and preservation validators pass. See the superseding note at the top of `FINAL-LAYOUT-QA.md`.
