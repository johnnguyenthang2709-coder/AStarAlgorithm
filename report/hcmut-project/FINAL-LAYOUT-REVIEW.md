# Final layout review

> Historical review of the preceding revision. The current comprehensive review is in `FINAL-LAYOUT-QA.md`.

## Scope and baseline

Reviewed the actual PDF from commit `597db50` (22 physical pages) on `codex/hcmut-project-report`. The attachment's `report(6).pdf` filename was not provided as a separate accessible artifact; the current compiled repository PDF was used as the before baseline. The final report still has 22 physical pages: cover, two Roman-numbered front-matter pages, and 19 Arabic-numbered body/reference pages.

## Issues and retained corrections

- The student table was left aligned. A centered `tabular` now retains left-aligned names/class and right-aligned IDs, the original column spacing, all five exact Vietnamese names, and class CC06. Poppler's visible-text bounding box is centered to within 0.003 pt of the page center.
- Architecture figures previously interrupted split explanatory paragraphs. `samepage` groups retain the partial-edge explanation and ancestry explanation as complete paragraphs. The original full-width graphics remain close to their introductions; neither was shrunk. Figure 1 now shares physical page 8 with its introduction.
- Physical page 15 was a road table/chart float-only page, with interpretation broken across surrounding pages. A targeted `Needspace` before Results and a protected interpretation paragraph now put Section 7.1's introduction, Table 2, Figure 3, and complete interpretation on physical page 15.
- Figure 4 now shares physical page 16 with the Section 7.2 introduction and Table 3. The paired-length paragraph remains complete and introduces Figure 5 on page 17. Remaining robot figures stay in numeric order and near their substantive discussion.
- References previously split across physical pages 21–22. A targeted `Needspace` before the bibliography now retains all nine entries on physical page 22. Its contents entry and hyperlink anchor are created after the space check.
- Float fractions allow more mixed text/float pages (`topfraction=0.85`, `bottomfraction=0.7`, `textfraction=0.1`, `floatpagefraction=0.8`), with up to three top floats/four total floats. `!htbp` permits appropriate placements. Widow/club penalties of 3000 discourage isolated lines without forbidding every paragraph break.
- No additional `clearpage`, `newpage`, or `FloatBarrier`, negative vertical space, font reduction, margin change, or line-spacing change is retained. Trial barriers and reduced diagram sizing were rejected because they produced worse pagination.

## Section 3 correction requested during review

Section 3 was previously moved wholesale to physical page 7 even though page 6 had space for its headings and introduction. The opening block plus equation exceeded the remaining space, and LaTeX's default `predisplaypenalty=10000` forbade a break before the display. A local group sets `predisplaypenalty=0` for Equation (3) only, allowing the section and introductory text onto physical page 6 while the equation follows on page 7. No explicit new-page instruction caused the original transition. This change also lets Figure 1 appear beside its introduction on page 8. The updated ToC correctly places Section 3 on printed page 3.

## Before/after physical placement

| Material | Before | After |
|---|---:|---:|
| Figure 1: architecture | 9 | 8 |
| Figure 2: road geometry | 10 | 9 |
| Table 1: snapshot eligibility | 13 | 13 |
| Table 2: road results | 15 | 15 |
| Figure 3: road effort | 15 | 15 |
| Table 3: paired robot outcomes | 16 | 16 |
| Figure 4: observed geometry | 17 | 16 |
| Figure 5: paired lengths | 17 | 17 |
| Figure 6: validity | 18 | 18 |
| Figure 7: runtime | 19 | 19 |
| Figure 8: supporting behavior | 20 | 20 |
| Section 3 opening | 7 | 6 |
| Algorithm 1 | 11 | 11 |
| Conclusion | 21 | 21 |
| References | 21–22 | 22 |

Identical page numbers do not imply identical placement: page 15 now contains the complete road discussion, rather than only floats; page 17 integrates the length plot with its interpretation.

## Verification actually performed

```powershell
& report/hcmut-project/scripts/build.ps1
py -3.14 report/hcmut-project/scripts/render_qa.py
py -3.14 report/hcmut-project/scripts/validate_report.py
pdftotext -bbox-layout report/hcmut-project/report.pdf <temporary-bbox-file>
git diff --exit-code -- report/springer-lncs
git diff --check
```

The validator invokes `experiments/benchmarks/validate_final_benchmark.py`. It verifies the 180 road pairs, 351 captured robot states, 21 eligible robot pairs, and all 56 frozen artifact hashes, without rerunning or altering experiments. It also verifies all 53 frozen LNCS files, nine section bodies in sequence, the abstract, all eight figure files, three tables, nine bibliography entries/style, ToC section/subsection destinations including References, A4/12pt/2.5 cm geometry, embedded non-Type-3 fonts, and Unicode extraction with pypdf and Poppler. Added checks measure cover centering and verify each supplied name/class/ID association. Pagination-only groups are ignored for source equivalence; their enclosed text is compared unchanged.

The final build has no typesetting or unresolved-reference warnings. Every physical page was rendered at 120 dpi and inspected in six contact sheets; the cover and primary road-results page were also inspected at full size. Captions remain attached, the algorithm is intact, figures remain legible, and no clipping, unintended blank page, or stranded heading was observed. FACULTY OF APPLIED SCIENCE, the university name, supplied logo, borders, lecturer, and student data remain unchanged.

## Remaining compromises

- The Section 3 opening equation follows on physical page 7 after the headings and introductory text on page 6. Only this equation permits a preceding break; no mathematical content or display spacing changes. Figure 1 now shares page 8 with its introduction, and Figure 2 remains close to its road explanation.
- Figure 7 follows its component discussion on the next page, alongside continuation of the online-results text. It remains one page from its substantive introduction, with unchanged labels/caption.
- Some whitespace remains below the complete Conclusion on physical page 21. Keeping the nine-entry bibliography together produces a balanced final page without altering spacing standards or forcing a page-count target.
- Ordinary longer paragraphs still cross page boundaries. Eliminating every such break would create more whitespace. No assertion of perfect line-level pagination is made.

Only report files are changed. Production code, benchmark artifacts, the authors' checkout, scientific wording, mathematics, citations, and the Springer LNCS manuscript remain unchanged. No merge or push is performed.
