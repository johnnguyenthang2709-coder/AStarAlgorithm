# Final editorial polish

2026-10-09. Branch: `codex/springer-lncs-final-editorial`, derived from `f9475d0`.
This is a local precision pass, not a manuscript rewrite. All nine sections were reviewed; Section 8 required no changes.

## Substantive changes

Pages refer to the final compiled PDF.

| Section/page | Original wording | Revised wording | Reason |
|---|---|---|---|
| Abstract / 1 | “The contribution is an implemented, reproducible educational system, without claiming globally optimal navigation in unknown space.” | “The implementation provides a reproducible case study of graph-optimal planning and conditional recovery under partial observability.” | Positive scope statement; limitations remain in the abstract and body. Abstract remains 165 whitespace words. |
| Introduction / 1 | “Available information determines what a shortest path can mean.” | “The information available to a planner determines which paths it can evaluate and optimize.” | Specifies the effect of knowledge on planning. |
| Introduction / 2 | “Phan et al. [8] require blind-alley escape not to exceed the entry length.” | “Phan et al. [8] investigate navigation through blind-alley regions and analyze return-path properties under stated geometric assumptions.” | Avoids implying an unconditional method-wide guarantee. |
| Contributions / 2 | “The contribution is a reproducible implementation, conditional executed-return certificate, and controlled evaluation. It establishes neither new A* theory nor global unknown-world optimality.” | “The contribution is a reproducible implementation and controlled evaluation of shared graph search, together with a conditional executed-return certificate. Its scope is established A* theory and observed-graph planning; global unknown-world optimality is not established.” | Leads with verified contributions while retaining the limits on novelty and optimality. |
| Related work / 4 | “Dijkstra is background.” | “Dijkstra is discussed as a foundational search method rather than evaluated as an independent experimental baseline.” | Refers specifically to the authors' study. The following sentence identifies Dijkstra-style skeleton search preceding bundle refinement, separately from grid A* experiments. |
| Formulation / 5 | “A successful alley exit is called certified only when the stated anchor, reversible trajectory, and executed-length checks hold.” | “A return to an observed ancestor is certified only when the recorded entry trajectory is reversible and the executed return satisfies the prescribed endpoint and length constraints.” | Certification does not establish exit from a geometrically defined BAR. |
| Sensing / 7 | “Benchmark annotations therefore cannot resolve unknown space for target selection or recovery.” | “Ground-truth annotations are used only for evaluation and do not influence target selection or recovery decisions.” | Distinguishes evaluation labels from sensor/executor access to physical ground truth. |
| Implementation / 8 | “CLOSED thus records expansion history without preventing reopening.” | “The last-expanded g-score records expansion history without permanently closing a state, thereby allowing reopening when a strictly better path is found.” | Matches `Record.expanded_g`, not a permanent CLOSED set. Nearby stale-entry sentences are condensed without changing the two checks. |
| Methodology / 10 | “A manifest description saying 6,000 reachable distances is a wording discrepancy; actual selection uses 5,965.” | Removed from the narrative; the preceding description now states “retaining 60 queries each for 180 frozen benchmark queries.” | Keeps 6,000 sampled, 5,965 reachable, and 180 selected; historical discrepancy remains below and in scientific QA. |
| Results / 14 | “The largest difference, P02-_map_deadend-01, is 15.734 versus 60.000 units, with ASP boundary contact.” | “A dead-end configuration with the largest difference (P02-_map_deadend-01) yields 15.734 units for ASP versus 60.000 for A*, with ASP boundary contact.” | Names the setting naturally, keeps trace identity, assigns each length explicitly. “Strict validity passes ASP” is also corrected to “ASP passes strict validity.” |
| Conclusion / 18 | “The system provides a reproducible algorithms demonstration connecting search, geometry, and exploration.” | “The resulting implementation and evaluation provide a reproducible case study of graph search under different assumptions about environmental knowledge.” | Research-oriented synthesis without claiming algorithmic novelty. |

## Factual rechecks

- Phan et al.: Introduction defines the return-length objective; Sections 3 and 4.5 discuss geometric representation/refinement assumptions. Section 4.6 explicitly qualifies general convergence; Section 5 concerns restricted Algorithm 3 assumptions. No restricted theorem is transferred to our controller. Section 6.1 distinguishes the geometric method from its grid A* baseline. Pinned `Graph.py:38–56` uses cumulative Euclidean cost in a priority queue.
- `include/astar/search.hpp:57,94–97` stores an optional last-expanded cost and skips stale or non-improving entries. Algorithm 1 and all implementation code are unchanged.
- `backend/app/services/bar_continuous.py:364–408` verifies reverse-entry feasibility, proposed endpoints/length, and measured executed return to the selected ancestor. This is the certification described in Sections 3.3 and 5.3, not universal BAR detection.
- Sensing and evaluation separation is retained from the source-to-claim evidence in `SCIENTIFIC-QA.md`. Physical ground truth remains available to simulation sensing and motion checks; annotation labels do not become policy inputs.
- Raw road rows independently give 180 equal-cost pairs, 180 with fewer A* expansions, and 173 with lower measured A* time. The existing validator confirms 76.0% expansion reduction and 0.338 paired time ratio.
- The existing validator confirms robot 351/21 selection, lengths 9/10/2, zero median difference, interior-valid 21/21 both, strict-valid ASP 15/21 and A* 21/21.

**Reproducibility note:** The historical manifest describes 6,000 reachable distances, while the actual frozen selection uses 6,000 sampled candidates and 5,965 reachable candidates. The manifest remains unchanged. This already documented wording error does not change the 180-query sample or results.

## Actual QA results

All commands run from the repository root:

```powershell
& report/springer-lncs/scripts/build.ps1
py -3.14 report/springer-lncs/scripts/validate_report.py
py -3.14 report/springer-lncs/scripts/validate_pdf_text.py
py -3.14 report/springer-lncs/scripts/render_qa.py
git diff --check
```

- Build: PASS; zero final overfull/underfull boxes, unresolved references, or LaTeX/package warnings.
- Scientific/numeric checks: PASS; all 56 benchmark hashes unchanged, pinned authors checkout clean, all nine references cited.
- Text extraction: PASS in pypdf and Poppler; all 23 font resources have Unicode maps, no Type 3 resources, no unexpected control/replacement characters. Ligature words, accented names, and representative mathematical symbols extract correctly.
- Layout: all **19 pages** rendered at 120 dpi and visually inspected. References now begin on page 19. Extra wording changes standard float/page placement; no class, font size, margin, float rule, figure or table was changed to force the earlier 18-page count. Algorithm 1 fits completely on page 9; figures/captions and all nine references are legible. No clipping, overlap, or typography defect found.
- The Git diff was inspected: only the requested sentences and immediately related clarification/conciseness corrections changed. Production tests were not rerun for wording-only edits. Historical baseline regression evidence is preserved.

## Exact modified files

All paths below are relative to `report/springer-lncs/`:

- `main.tex`
- `sections/01-introduction.tex`
- `sections/02-background.tex`
- `sections/03-formulation.tex`
- `sections/04-architecture.tex`
- `sections/05-implementation.tex`
- `sections/06-methodology.tex`
- `sections/07-results.tex`
- `sections/09-conclusion.tex`
- `report.pdf`
- `validation.json`
- `pdf-text-validation.json`
- `SCIENTIFIC-QA.md` (supplement only)
- `LAYOUT-QA.md` (supplement only)
- `EDITORIAL-CHANGELOG.md` (new)

`WRITING-STYLE-REVIEW.md` is preserved as the prior revision record. Bibliography, metadata, official class/style, font setup, figures/tables, algorithm logic, scripts, production code, raw results, and the authors' checkout are unchanged. Supplied untracked papers are preserved. No merge or push is performed. Verified author/affiliation information is still required before submission; venue-specific page limits should be checked against the 19-page artifact.
