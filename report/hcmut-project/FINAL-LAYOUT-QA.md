# Final comprehensive layout and pagination QA

## Latest update: Section 8 spacing and references-only final page

Section 8 uses run-in `\paragraph` labels, not numbered subsections. Their default article-class pre-heading spacing was 3.25ex. A scoped, checked `\patchcmd` reduces it to 1.5ex only around Section 8; the original heading spacing resumes for Section 9. The final supporting figure (Figure 8) is uniformly reduced by 5%, from full text width to 0.95 text width. All other figure sizes and caption spacing remain unchanged. Trial reductions of multiple figures alone did not move the conclusion tail and were discarded.

The requested final sentence now ends on physical page 20, and physical page 21 contains only References. The total remains 21 pages. No section page breaks, body font changes, margin changes, line-spacing reductions or scientific text edits were introduced. Pages 19–21 were individually inspected after re-rendering; the final figure labels remain readable, Section 8 labels have clear but smaller separation, and all nine bibliography entries fit intact. Project build and full report validators pass, including all frozen-content checks. The validator recognizes the new figure width as a layout-only difference while independently requiring identical figure PDF bytes. Built-in editor compilation still has its documented pdfTeX/XeTeX Unicode incompatibility.


## Latest update: standard first-line indentation

Added `\usepackage{indentfirst}` and retained `\setlength{\parindent}{1.5em}` in `main.tex`. Normal paragraphs immediately after section/subsection headings now receive the same first-line indent as other normal paragraphs, including the abstract text. Explicit unindented cover labels and the keywords label remain intentional non-body elements. No manuscript content or section-break controls were changed.

Rebuilt using the existing pdfLaTeX/BibTeX script, rendered all pages at 120 dpi and inspected all six consecutive contact sheets. The report remains 21 physical pages; Section 2 still follows Section 1 on physical page 4. No clipping, heading isolation or new pagination defect was found. Build and all report/reference/Unicode/frozen-artifact validators pass without warnings. No further layout edits were necessary. The editor's existing XeTeX incompatibility with pdfTeX Unicode mapping remains separate from the successful project build.


## Latest correction: gap after Section 1

The earlier correction removed explicit section controls but left paragraph/display penalties at 10000, which still prevented Section 2's opening from using the available space. These penalties are now preferences (3000), and the pre-display penalty is 0. This permits normal breaks before a display without changing text, equation structure, fonts, margins or line spacing. Section 2 now starts directly after Section 1 on physical page 4; Section 3 follows the preceding text on physical page 6. No body section break/reservation/barrier was added.

The current PDF has 21 physical pages. All consecutive contact sheets were reviewed, including the Section 1–2 transition at full resolution. Build passes without typesetting warnings. The reference-placement validator was updated to check the correct References heading/page rather than require it at the top: a two-line conclusion continuation now precedes References on physical page 21. Bibliography entries, citations and frozen-content checks are unchanged. Earlier counts/placement observations below are historical and superseded by this note. The built-in XeTeX preview limitation remains; the project pdfLaTeX build is authoritative.


## Superseding correction: continuous section flow

Following the explicit user instruction, all body-section and subsection `\Needspace` reservations and `\FloatBarrier` commands have been removed. Sections 1–9 use normal article flow. No `\newpage`, `\clearpage` or `\pagebreak` occurs between these sections or inside their source files. The front matter and bibliography retain their existing separate handling. Natural TeX page breaks, including headings moving when insufficient space remains, are permitted; sections are not assigned a new page.

The rebuilt PDF remains 22 physical pages. The pdfLaTeX/BibTeX build and full report validators pass without typesetting warnings. All consecutive contact sheets were reinspected; the approved cover and scientific content remain unchanged. Table 1 now appears on physical page 13; Sections 6, 7, 8 and 9 begin within physical pages 12, 14, 19 and 20 respectively. Sections 2 and 3 still naturally start on physical pages 5 and 7. The earlier page-placement table and retained-control discussion below document the previous revision and are superseded by this correction. Font, margin, spacing, equations, figure data and frozen benchmark preservation checks remain unchanged. Current mapped font-instance count: 128.


## Baseline and scope

Reviewed on `codex/hcmut-project-report`, starting from commit `bba24a3` and the existing local cover revisions. The accessible baseline was the current repository `report.pdf`, with 22 physical pages. A separate `report(7).pdf` was not available. Baseline source/PDF/render copies are preserved locally in `tmp/pdfs/hcmut-layout-before/`; they are not submission artifacts.

The final PDF has **22 physical pages**: cover, abstract and contents with Roman numbering, then 19 Arabic-numbered body/reference pages. No page-count target was imposed. All final pages were inspected individually at 120 dpi and in consecutive-page contact sheets. The persistent overview is [assets/layout-overview.png](assets/layout-overview.png).

The approved cover is unchanged relative to the working-tree baseline: identical metadata source and pixel-identical page-1 rendering. It retains Faculty of Applied Science, PROJECT REPORT CALCULUS 1, lecturer Phan Thanh An, class CC06, the exact five accented names/IDs, logo and three borders. The student-table center offset is 0.002648 pt. Previously authorized cover changes already present before this audit are included in the report commit, rather than discarded.

## Page-by-page review

Numbers below are physical PDF pages. Initial findings refer to the baseline; final decisions reflect the complete re-render, including adjacent transitions.

| Page | Initial finding, severity and root cause | Final inspection / correction |
|---:|---|---|
| 1 | None: approved cover, balanced hierarchy and centered student information. | Preserved; pixel-identical to baseline. All diacritics, borders and logo clear. |
| 2 | None: abstract and keywords fit with appropriate front-matter space. | Preserved. Roman page i; no orphan or overflow. |
| 3 | None: contents fit on one page. | Regenerated; every numbered destination checked against actual PDF pages. Roman page ii. |
| 4 | Moderate: Section 2 and its short equation introduction stranded below the Introduction. Insufficient opening-space reservation. | Introduction now ends naturally; Section 2 opens on page 5. Remaining space is preferable to a two-line mathematical opening. |
| 5 | Minor: short subsection opening split into the next page. | Theory heading, shortest-path introduction and Equations 1–2 form coherent units. No clipped displays. |
| 6 | Major: Section 3 definitions began at the foot, with their optimization equation on page 7. Local permission to break before the display aggravated separation. | Observation/exploration and BAR literature occupy page 6; formulation begins with its definitions and Equation 3 together on page 7. |
| 7 | Moderate: principal equation appeared without its preceding heading/definitions. | Full formulation opening and both road/grid displays grouped naturally. Recovery-objective subsection follows on page 8 with a meaningful opening. |
| 8 | Minor: large architecture diagram increased float pressure. | Figure 1 is 80% text width, aspect ratio preserved and labels readable. It remains with its Section 4.1 introduction. |
| 9 | Moderate: sensing subsection opened with only two lines after the road figure. | Road representation and Figure 2 stay together. The complete reuse paragraph from Section 4.1 precedes them; sensing opens on page 10. |
| 10 | No major defect: ancestry and algorithm opening require continuity. | Sensing opening, observed-ancestry description and algorithm section opening remain coherent. No hidden-state or scientific wording changes. |
| 11 | Minor: application-heuristic opening and short proof unit split into page 12. | Algorithm 1 and its introductory paragraph are intact. Section 5.2 moves with its proof opening to page 12. All pseudocode lines retained. |
| 12 | Moderate: methodology opening at foot competed with the return-certificate discussion. | Haversine/grid/Euclidean discussion and Equation 5 certificate remain intact; methodology opens on page 13. Some lower space is accepted to protect that opening. |
| 13 | None in table contents; placement depended on preceding pagination. | Section 6 and source-audit/eligibility introduction read continuously. Table 1 follows at the top of page 14, still in Section 6.2. |
| 14 | Moderate: substantial lower space before the Road results grouping; short exclusion discussion could fragment. | Table 1, complete exclusion paragraph and Section 6.3 fill the page more evenly. Remaining space protects the coherent Road-results page. |
| 15 | None: good Road results/table/figure/interpretation grouping. | Preserved: Table 2 and Figure 3 stay after their introduction within Section 7.1. All data and labels readable. |
| 16 | None: paired robot introduction/table/representative plot grouped well. | Preserved: Table 3 and Figure 4 within Section 7.2. Captions attached and unobstructed. |
| 17 | None: paired-length plot and interpretation coherent. | Figure 5 and its analyses remain legible and complete. No artificial compression. |
| 18 | Moderate: runtime plot queued to the next page, separating computation discussion. | Figures 6 and 7 now share the relevant computation discussion; both use 80% width with readable axes/legends. |
| 19 | Moderate: queued runtime plot interrupted computation text; online-recovery plot delayed until limitations. | Complete computation paragraph, online-recovery introduction and Figure 8 appear here. No unrelated float interrupts Section 8. |
| 20 | Moderate: Figure 8 interrupted limitations; short reproducibility paragraph split at page foot. | Certified-return paragraph remains complete, followed by Section 8. Long sampling paragraph may break normally; no late figure intrusion. |
| 21 | Moderate: isolated reproducibility tail; conclusion followed with unused lower space. | Two-line continuation of the longer sampling paragraph is accepted. Short reproducibility and future-work units are complete; Conclusion remains coherent. Lower space is accepted before the full bibliography. |
| 22 | None: all nine references fit on one readable page. | Preserved full bibliography, resolved citations, intact entries and searchable Unicode. No attempt to force an 18/21-page result. |

## Retained LaTeX changes

- `main.tex`: targeted `\Needspace` for background, formulation and methodology openings; `\FloatBarrier` before limitations; widow, club and display-widow penalties of 10000. Existing Road-results reservation and bibliography grouping retained. Font size, margins, caption design, line spacing and float parameters are unchanged.
- `sections/03-formulation.tex`: removed the local `\predisplaypenalty=0` group. Together with the opening reservation this keeps definitions with the first optimization equation.
- `sections/04-architecture.tex`: Figure 1 at `0.8\textwidth`; barriers before the next architecture subsections; meaningful sensing-opening reservation. Figure 2 remains full width.
- `sections/05-implementation.tex`: protect the brief algorithm introduction with `samepage`, reserve a useful Section 5.2 opening.
- `sections/06-methodology.tex`: keep the brief direct-exclusions paragraph together.
- `sections/07-results.tex`: Figures 6–7 at `0.8\textwidth`; keep the short computation and certified-return interpretations together; barrier before online behavior.
- `sections/08-limitations.tex`: keep short reproducibility and future-work discussions together. The longer sampling paragraph is deliberately not forced onto one page.
- `scripts/validate_report.py`: recognize only the additional pagination wrappers and uniform figure sizing when comparing scientific text; verify the already-approved uppercase cover/course wording. Independent figure-byte, table, bibliography and benchmark preservation checks remain active.
- Refreshed cover preview and added the final page overview. No scientific wording adjustment was needed.

No new body `\clearpage`/`\newpage`, forced `[H]` floats, `\enlargethispage`, negative spacing, font reduction or geometry changes were introduced. The three resized diagrams retain aspect ratio and original figure bytes.

## Before / after placement

| Item | Baseline physical page | Final physical page |
|---|---:|---:|
| Section 2 opening | 4 | 5 |
| Section 3 opening / Equation 3 | 6 / 7 | 7 / 7 |
| Figure 1: architecture | 8 | 8 |
| Figure 2: Road geometry | 9 | 9 |
| Section 4.3 opening | 9 | 10 |
| Algorithm 1 | 11 | 11 |
| Section 5.2 opening | 11 | 12 |
| Section 6 opening | 12 | 13 |
| Table 1: snapshot eligibility | 13 | 14 |
| Table 2 / Figure 3: Road results | 15 | 15 |
| Table 3 / Figure 4: robot results | 16 | 16 |
| Figure 5: paired lengths | 17 | 17 |
| Figure 6: validity | 18 | 18 |
| Figure 7: computation | 19 | 18 |
| Figure 8: online behavior / recovery | 20 | 19 |
| Conclusion / References | 21 / 22 | 21 / 22 |

## Iteration and stopping decision

Each material edit was rebuilt and re-rendered. An intermediate 90%-width architecture/barrier trial increased the document to 23 pages and left awkward space; it was rejected. The retained 80% diagram is readable and preserves the 22-page balance. Subsequent paragraph grouping and stricter widow penalties removed isolated short fragments without enclosing the long limitations paragraph.

Remaining compromises are ordinary typesetting trade-offs: the architecture reuse paragraph follows on page 9; Table 1 follows its eligibility introduction on page 14; the long sampling paragraph ends with two lines on page 21. Pages 4, 12 and 21 have some lower whitespace because coherent equation/section/bibliography units were preferred. All floats stay in the relevant discussion. Further forced breaks or compression would cost readability and maintainability.

## Preservation and validation evidence

- Final project build: pdfLaTeX + BibTeX, three LaTeX passes, exit 0. No overfull/underfull boxes, unresolved references, font substitutions or LaTeX/package warnings.
- Validator: **PASS**, 22 pages, A4 article/12pt/one column/2.5 cm margins/1.15 spacing. All 11 contents section entries and subsection destinations match pagination.
- Both pypdf and Poppler extraction pass; 132 font instances are embedded, non-Type-3 and have Unicode maps. Exact approved cover names/course/institutions pass.
- All nine scientific section sequences additionally match the current pre-audit commit `bba24a3` after removing only layout controls; no prose, equations, pseudocode or citations changed.
- Eight figure PDFs remain byte-identical, all three table contents and nine bibliography entries/style are unchanged, and 53 frozen Springer files remain unchanged.
- All 56 benchmark artifact hashes match the frozen manifest. Frozen benchmark revision: `04c48468c6b6b4f6512be925383614267fa7ca32`. Road remains 180 pairs/equal costs, median expansion reduction 76.0%, time ratio 0.338. Robot remains 351 decisions/21 eligible pairs; ASP shorter 9, A* shorter 10, equal 2; interior validity 21/21 each, strict ASP 15/21 versus A* 21/21. Blocked 48-case end-to-end comparison and all assumptions retained.
- The built-in editor compiler was also attempted after the final source edit. Its Tectonic/XeTeX engine cannot execute this project's pdfTeX-specific `\pdfglyphtounicode` command. This preview limitation is explicitly reported; the successful project pdfLaTeX build is authoritative. No Unicode mapping was removed to accommodate the editor engine.
- This is a report-only change; production regression suites and experiments were not rerun or modified. Existing frozen artifacts were verified, not regenerated.

### Reproduction commands (PowerShell, repository root)

```powershell
& report/hcmut-project/scripts/build.ps1
py -3.14 report/hcmut-project/scripts/render_qa.py
py -3.14 report/hcmut-project/scripts/validate_report.py
git diff --check
```

`validation.json` records machine checks. `qa-render/` contains all 120-dpi pages and consecutive contact sheets locally; `assets/layout-overview.png` is the committed overview. Automated validation complements, rather than replaces, the full visual review.

## Submission status

Final LaTeX: `main.tex` and existing component sources. Final PDF: `report.pdf`. Dedicated branch unchanged; report-only commit, no push or merge. External papers, local baseline renders, production sources, benchmark outputs and Springer manuscript are preserved.
