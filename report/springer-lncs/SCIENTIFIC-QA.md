# Scientific QA

Date: 2026-10-09. Original reporting branch: `codex/springer-lncs-report`; writing revision: `codex/springer-lncs-writing-refinement` from `861e120`. Authoritative baseline: `04c48468c6b6b4f6512be925383614267fa7ca32`. This review produced documentation only.

## Writing-revision consistency check

The revised exposition preserves the source-to-claim evidence below. The final report and benchmark validators were rerun: all 56 frozen hashes, principal paired statistics, and newly explicit 21/21 interior and 15/21 versus 21/21 strict-validity assertions pass. Figures, tables, bibliography, metadata, and official class/style remain byte-identical to `861e120`. Production regression executions below are preserved historical results from that baseline, not reruns in this writing-only revision. The original PDF's ligature/Unicode defect was independently reproduced and corrected; both extraction engines pass the new check. Details and before/after review are in `WRITING-STYLE-REVIEW.md` and `pdf-text-validation.json`.

## Source-to-claim review

| Claim / distinction | Independently inspected source and evidence | Disposition |
|---|---|---|
| Shared A*, best-g updates, lazy entries, reopening, goal extraction, parents | `include/astar/search.hpp:46–143`, especially stale checks 94–95, goal 102, relaxation 125–136 | Algorithm 1 matches actual logic. No permanent CLOSED flag; finite-cost checks do not establish admissibility. |
| Tie order and search counters | Same header, entry comparator and result definitions | f, h, insertion order; deterministic only given deterministic neighbors. Valid pops include goal/reopen; generated pushes include duplicates. |
| Road consistency and graph size | `src/road_problem.cpp:38–78`; `road-validation.json`, raw road CSV, final manifest | Scale 1.0, zero edge violations; 2,986 / 7,152; 180 equal costs. |
| Coordinate snapping and directionality | `src/edge_snapped_road_problem.cpp`, projection, `directions`, constructor, `add_partial`, route reconstruction | Local projection, along-polyline fractions, same-edge order, own reverse costs, request overlay, lower-bound rescaling; node experiment distinguished from snapping. |
| Grid costs | `include/astar/grid_problem.hpp` | Educational diagonal cost is **1.5**, not sqrt(2); BAR four-direction cost 1. |
| C++ versus Python responsibilities | `backend/bindings.cpp`, `bar_continuous.py:308–329`, routers and frontend playback | Geometry/controller in Python; Euclidean graph search in C++; UI interpolation is not added execution. |
| Knowledge and hidden map | `bar_continuous_geometry.py` sensor/collision functions, `ContinuousPolicy.observe`, `backend/app/routers/bar.py:17–24` | Ground truth only sensor/executor/evaluator; policy receives observations. No hidden-room oracle claimed. |
| Information gain and ancestry | `bar_information.py:26–65`; `bar_continuous.py:23–31, 130–307` | Gain is approximate; direct-distance discount is not a planned A* cost; graph-blocked target is not exhaustion; candidates transferred/preserved. |
| Actual executed return bound | `bar_continuous.py:364–408, 440–460`, `docs/bar-indoor-radar-trace.csv` | A* attempt, route/endpoints/known-free/length check, verified reverse fallback, locked execution; four nonfallback certified events. The fourth trace return is shorter (7.729214 vs 7.910052); not all returns are shortcuts. |
| Source motion versus paper | Pinned `Robot_run.py:92, 126–150`, `Robot_class.py:77–95`, `Graph.py:38–56`; paper Algorithms 1–3 and §§3–6; motion audit | Coordinate jumps are not proof of straight physical motion. Planned ASP validity remains separate. Gate retained; no claim DAP theory is invalid. |
| Robot eligibility and graph differences | `robot-snapshot-eligibility-audit.csv`, three frozen snapshot manifests; `robot_local_geometry.py`, local benchmark scripts | 351/21/330; 176 visible +154 boundary direct exclusions; no outcome filtering. Same sights/endpoints, different graphs. |
| Geometry and footprint | `robot-local-final-paired.csv`, geometry-validation CSVs | Interior valid 21/21 both; strict ASP 15/A*21; radius-0.5 9/11 is diagnostic only. All boundary shorter results retained. |
| Timing | `road_benchmark.cpp:24–36, 77–97`; timing JSON/CSV | **Road median of seven batch means per call**, after one untimed call per method, batches 20/10/5. Historical prose says batch medians in one place; source controls. Robot 3 warm-ups/31 calls; component medians not algorithm-only speedup. |
| Literature metadata and assumptions | All eight PDFs recursively inventoried, primary metadata cross-checks, matrix | Seven unique works; third TangentBug author Elon Rimon retained; Theta* journal year 2010, Phan journal year 2026. Restricted convergence not transferred to our controller. |

## Independent numeric checks

`scripts/validate_report.py` and the existing benchmark validator passed. All **56** frozen artifact SHA-256 values match. The read-only checker also verifies clean pinned authors checkout and 69 local benchmark-document links.

- Road: 180 cost matches; 180 fewer expansions; 173 faster/7 slower; median paired expansion reduction 76.013866%; median time ratio 0.337609. Stratum table cross-checked against frozen raw rows.
- Robot: 21 pairs; 9 ASP shorter/10 A* shorter/2 equal; delta mean +2.981415, median 0; all 21 primary-valid, ASP15/A*21 strict-valid. Tables preserve 6/1/14 cohort composition.
- Source-state sampling and link checks: 175,500 membership samples, 111,672 link samples, 865 source ASP segments, 1,128 admitted A* links. Boundary predicate differences are separated from membership validation checks.
- Supporting: radar18 shorter/2 longer, largest unfavorable +70.771691; cache20/20 equivalent; sensor12/12 success; four certified nonfallback returns. No whole-world completion claim.

The report documents one frozen manifest wording discrepancy (6,000 candidate versus 5,965 reachable road distances) without rewriting any historical artifact.

## Fresh regression execution

Executed on the unchanged production tree, 2026-10-09:

| Actual command | Actual result |
|---|---|
| `.venv/Scripts/ctest.exe --test-dir build-cpython --output-on-failure` | **4/4 passed**, core/road/reference/edge_snap; 1.01 s reported total. |
| `.venv/Scripts/python.exe -m pytest -q tests` | **169 passed**, 116.29 s; one existing Starlette/httpx deprecation warning. |
| `npm run test` (frontend) | **34/34 passed**, 8 files; 30.86 s. |
| `npm run build` (frontend) | TypeScript and Vite build passed, 85 modules; no hosting started. |
| `npm run lint` (frontend) | Passed, exit 0. |
| `py -3.14 experiments/benchmarks/validate_final_benchmark.py` | PASS, authors clean, road180, snapshots351, pairs21, frozen figures14. |
| `py -3.14 report/springer-lncs/scripts/make_figures.py` | Eight report figures; frozen hashes verified. |
| `& report/springer-lncs/scripts/build.ps1` | pdfLaTeX/BibTeX/passes completed, no final overfull/underfull boxes, warnings, or unresolved references. |
| `py -3.14 report/springer-lncs/scripts/validate_report.py` | PASS: sections9, figures8, tables3, algorithm1, references9, abstract165 whitespace words, pages18. |
| `py -3.14 report/springer-lncs/scripts/render_qa.py` | All18 current pages rendered at120dpi and reviewed; see layout record. |

## Issues encountered and resolved

Initial report tooling failed on the Windows default CP1252 decoding of the UTF-8 road graph; explicit UTF-8 fixed that. An initial figure invocation used a repository-root relative path while already in the report directory; the documented root command corrects it. An assumed A4-media assertion in the report validator was incorrect: the actual unmodified class/article configuration emits 612×792-point Letter media, with the fixed LNCS 12.2×19.3-cm content area. The assertion now checks that actual class configuration. These were report-tooling issues, not production regression failures or changes to benchmark checks.

Typesetting iterations resolved prose overflow, the standard LLNCS vector/amsmath conflict, and chart legend/diagram-label overlaps. Natural-bottom alignment removes stretched float-page gaps without changing the class text area, font sizes, or paragraph spacing. The upstream README and sample contain two original trailing-whitespace lines; they are retained to preserve official resource hashes. Authored files pass the whitespace check. Report-local attributes prevent Git line-ending conversion of checksum-pinned official resources.

## Claims deliberately excluded

No global shortest online journey, universal BAR recognition/completion, disk-robot safety, author-algorithm inferiority, significance claim, paper-table reproduction, or intrinsic Python/C++ algorithm speedup. No blocked end-to-end values are promoted to comparisons. Existing Road Navigation, A* code, benchmarks, and authors checkout remain intact. Author/affiliation metadata need verified user values before submission.
