# Scientific writing and mathematical exposition review

Date: 2026-10-09. Revision branch: `codex/springer-lncs-writing-refinement`.
Before: complete report at `861e120`; underlying experimental baseline remains `04c4846`.

## Reference-informed approach

The supplied Phan et al. paper was re-read in its Introduction, Sections 3, 4.5–4.6, 5, and 6.1–6.2. Its useful expository pattern is to introduce the navigation difficulty, define available space and path objects, develop the geometric mechanism, and interpret experiments under stated assumptions. We adopted that progression, not its sentences, figures, bundle method, or theoretical guarantees. The reference explicitly distinguishes its general Algorithm 2 from its restricted convergence analysis; our manuscript preserves that distinction.

## Before-and-after review

| Aspect | Original presentation | Revised presentation |
|---|---|---|
| Research problem | Brief contrast followed by application inventory | Available information motivates fixed-graph optimization, exploration, and the return-length requirement. |
| Literature | Thematic, but some transitions begin directly with method names | Representation constrains optimality; changing observations motivates replanning; sensor knowledge motivates frontiers and recovery. All nine citations remain. |
| Mathematical formulation | Some objects are implicit; `x` appears in both decision and movement indexing | Finite directed graph and nonnegative weights precede the objective. `x_k` denotes decision position; `y_j` denotes executed position; `p_i` denotes recorded entry. Finite sums and indices are defined. |
| Architecture | Boundaries and structures stated as features | Knowledge separation, endpoint placement, ancestry, and numeric state records are explained through the problems they solve. |
| Search implementation | Correct update rules stated procedurally | Separating records from queue entries motivates lazy duplicates; stale checks explain safe termination and reopening. Algorithm 1 is unchanged. |
| Heuristic reasoning | Triangle inequalities mentioned | Road scale and the chained consistency inequality show why directed topology is compatible with the lower bound. Grid costs and Euclidean assumptions remain explicit. |
| Recovery reasoning | Recorded trajectory, inequality, then exclusions | Verified reverse entry supplies a feasible candidate; graph inclusion permits the A* bound; locked execution and measurement support certification. Fallback remains distinct. |
| Methodology | Audit and protocol facts | Three controlled questions motivate fixed-graph, shared-state local, and supporting online studies. Provenance is concise; all eligibility and validity restrictions remain. |
| Results | Mostly measurements plus caveats | Observations are connected to heuristic guidance, admitted path geometry, boundary conventions, construction cost, and exploration ordering. Proposed mechanisms are not presented as new experimental measurements. |
| Conclusion | Repeats several result counts | Synthesizes what information models permit us to conclude and identifies the remaining experimental questions. |

Source whitespace-token counts across the nine section files decreased from **4,789 to 4,750**. This is an auditable size comparison, not a linguistic word count. The abstract remains 165 whitespace words. Both versions have 18 physical pages, with references starting on page 18. Intermediate longer drafts were condensed; no font-size or margin adjustment was used to reduce length.

## Scientific consistency

- Road: 180 paired queries, 180 equal costs, 76.0% median paired expansion reduction, and 0.338 median paired time ratio are unchanged and recomputed from frozen rows.
- Robot: 351 captured decisions, 21 eligible comparisons; ASP shorter 9, A* shorter 10, equal 2; both interior-valid 21/21; strict validity ASP 15/21 and A* 21/21. The report validator now checks both validity counts explicitly.
- Sparse graphs, boundary conventions, point motion, Python/C++ timing stages, correlated samples, exploration regressions, and the blocked 48-case end-to-end comparison remain explicit.
- No new experiment, theorem, convergence result, global optimality claim, or transferred paper guarantee was introduced.
- Official class/style, bibliography, author metadata, all eight figure pairs, and tables are byte-identical to `861e120`; the text validator checks this. Production and benchmark files are unchanged; all 56 frozen result hashes pass.
- Existing production regression results in `SCIENTIFIC-QA.md` belong to the original completed baseline. They were not rerun for this documentation-only revision and are not described as new executions.

## Font-to-Unicode defect and correction

The original PDF contains Type 3 body fonts without ToUnicode mappings. Re-extracting the original committed PDF with pypdf reproduces control characters in ligatures, including “verified”, “different”, and “Affiliation”. The correction enables pdfTeX's standard `glyphtounicode` mappings and `pdfgentounicode=1`. The final build uses installed **CM-Super Type 1 outlines for the same T1 Computer Modern family**, retaining class fonts, sizes, content area, and layout conventions. CM-Super is a documented build prerequisite; no custom glyph substitution, disabled ligatures, or altered official class file is used.

The final PDF passes both pypdf and Poppler extraction: no replacement characters or unexpected control characters; ligature words, accented “Pérez”, and representative mathematical symbols are found. Every used font resource has ToUnicode mappings and none is Type 3. `pdf-text-validation.json` records the original defect and revised checks. Whitespace, reading order, and line-wrap hyphens remain extractor-dependent; a copied equation is not guaranteed to be structured mathematical markup.

## Actual revision QA commands

Run from the repository root:

```powershell
& report/springer-lncs/scripts/build.ps1
py -3.14 report/springer-lncs/scripts/validate_report.py
py -3.14 report/springer-lncs/scripts/validate_pdf_text.py
py -3.14 report/springer-lncs/scripts/render_qa.py
git diff --check
```

Compilation and all checks pass. Final log: zero overfull/underfull boxes, unresolved references, or package/LaTeX warnings. All 18 pages were rendered and visually inspected, with full-size checks of the algorithm, mathematical return argument, and final references. Early prose overflow was corrected by wording changes. See `LAYOUT-QA.md` and `validation.json` for final pagination and `SCIENTIFIC-QA.md` for the preserved source evidence.

No merge or push is performed. Untracked supplied papers and the clean pinned authors' checkout are preserved. Verified author/affiliation information is still required before submission.
