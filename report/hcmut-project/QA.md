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

The final document has **22 physical A4 pages**: cover (no printed number), abstract (i), contents (ii), and 19 Arabic-numbered body/reference pages. Introduction is physical page 4 with printed page 1. Contents is generated automatically, fits one page, and all numbered section/subsection destinations are checked against extracted page text. References begin on printed page 18 and continue on page 19.

The format check confirms `article[a4paper,12pt,oneside]`, a 160 mm x 247 mm text area (2.5 cm margins), one column, and 1.15 body line spacing. The contents page uses ordinary single spacing without reducing font size. The three nested cover rectangles are confined to the cover. Institution names, report topic, subtitle, and author remain within the frame. The official-logo placeholder is conspicuously labeled; no institutional emblem was fabricated. Optional administrative fields remain empty and invisible.

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

The formal cover and complete contents meet the written presentation brief; the original Calculus LaTeX example was unavailable, so exact template matching beyond that specification cannot be asserted. The official logo remains the only missing institutional asset. Administrative fields can be filled later with verified information. No integrity declaration or rights grant was assumed.
