# Final repository integration review

Date: 2026-10-10 (Asia/Saigon). Approved report baseline: `df8607a`.

## Git audit and integration method

- Repository: https://github.com/johnnguyenthang2709-coder/AStarAlgorithm
- Fetched `origin` before review and again before integration. Local and remote main both pointed to `ab0535d8a4b93aed519cf95882a03337b3396ce2`.
- All 17 completed local branches below are ancestors of `codex/hcmut-project-report`; the 39 existing commits absent from main form one linear history. Integration uses `git merge --ff-only codex/hcmut-project-report` after the documentation/security lockfile commit. No cherry-picks, history rewriting, forced push, branch deletion, or scientific edits are required.
- Initial untracked `tmp/` and `reference/Papers/` are preserved locally and now ignored. Tracked-path inspection found no virtual environments, dependency directories, temporary diagnostics, private paper directory, `.env` secrets, PEM/key files, Python caches, or LaTeX logs. Existing report PDFs, figures and QA artifacts are intentional deliverables.
- Largest tracked artifact: frozen prospective robot snapshots, 15,034,521 bytes, below GitHub's 100 MiB per-file limit.
- No TODO/FIXME/NotImplementedError markers were found in the inspected production source directories. This is not proof of universal navigation completeness; the research limitations below remain.

| Integrated branch | Audited tip before final documentation commit |
| --- | --- |
| `codex/academic-benchmark` | `da96440aa16c27a719b2827931e47ec48444a2bb` |
| `codex/academic-benchmark-final` | `04c48468c6b6b4f6512be925383614267fa7ca32` |
| `codex/author-motion-validity-audit` | `0631f6c2d089aec8d6afee834eee5e9db0a89b90` |
| `codex/bar-continuous-navigation` | `a83068099604a861460f69d6f16a23e1a90b37af` |
| `codex/bar-final-verification` | `c005b4d535e94c8f65389a4b9e2b33ca3de3b4da` |
| `codex/bar-frontier-performance` | `cb69fc65fb81f6cffdd3e0556f4dccd5892bdcdf` |
| `codex/bar-indoor-hierarchical` | `88ab9f9e3d64710e7051b3b6cc79e687c357a773` |
| `codex/bar-irregular-labyrinth` | `b8c4f4cc83d7736b375cc411b20fe9b3f3ec0fbc` |
| `codex/bar-large-simulation` | `aaf19d783255a7a20d40c5404ddb8d41de43bbb7` |
| `codex/bar-maze-3` | `d9e6c5151185579e71701166955ca325ccc70144` |
| `codex/bar-polygon-maps` | `345af2805cc4177becb6b8ef0608940301d80bae` |
| `codex/bar-radar-informed-exploration` | `01ced69b0c176d9bf0e89b75a265bc0ee0fd7c20` |
| `codex/hcmut-project-report` | `df8607a70ef7171eb129b38b37e91de76337db1a` |
| `codex/robot-local-shared-state` | `ead37b14ff300471dbc9c1e1a772431429f5e9f7` |
| `codex/springer-lncs-final-editorial` | `faaeb2ccb29bad21d6a1b64812cc495239419461` |
| `codex/springer-lncs-report` | `861e1200083a1099c1b50e1c69ad67a34f68df5b` |
| `codex/springer-lncs-writing-refinement` | `f9475d07bd192bfaf9d86a9e39a737d090dd889a` |

## Final changes made during integration

- `README.md`: completed application overview, shared-engine source guide, setup/build/test/start commands, existing diagnostic figure, report links, research attribution, frozen results and comparison limitations. Obsolete standalone demo measurements were removed in favor of the frozen benchmark package.
- `.gitignore`: preserve local temporary diagnostics and privately supplied papers without publishing them.
- `frontend/package-lock.json`: only `source-map-js` changed from 1.2.1 to 1.2.2, with its registry URL and integrity hash. Clean installation reported GHSA-68fv-2mgg-jv7q; this patch resolves the indexed-source-map denial-of-service advisory. No direct dependency specification or application source changed.
- `.gitattributes`: preserve frozen benchmark/report bytes, with explicit CRLF overrides for 42 historical benchmark serializations whose original hashes require CRLF; remaining frozen files keep Git bytes.
- This integration record.

No production algorithm, experimental measurement, benchmark artifact, LaTeX manuscript or approved PDF content was edited. A post-fast-forward validator caught Windows `core.autocrlf` converting frozen files to CRLF. Files were restored from raw Git blobs, applying LF/CRLF only where the existing manifests prove the original serialization; `.gitattributes` now preserves those exact per-file serializations on future checkouts; validators were rerun before publication. Historical report-directory READMEs retain their conversion-time wording; current PDFs, metadata and final validator outputs are authoritative.

## Validation commands and actual results

Environment: Windows CPython 3.12.10 application venv; Python 3.14 report validator environment; MSYS2 UCRT64 g++; Node 24.19.0; npm 11.17.0. Run application commands from repository root; frontend commands from `frontend/`.

| Command | Result |
| --- | --- |
| README CMake configure command using Ninja, Windows Python import library and pybind11 directory | PASS |
| `.venv/Scripts/cmake.exe --build build-cpython --parallel 4` | PASS; existing compiled targets current |
| `.venv/Scripts/ctest.exe --test-dir build-cpython --output-on-failure` | 4/4 suites PASS |
| `PYTHONPATH=backend` then `.venv/Scripts/python.exe -m pytest -q tests` (PowerShell environment assignment in README) | 169 PASS; one existing Starlette/httpx deprecation warning; 57.87 s |
| `.venv/Scripts/python.exe -m unittest discover -s tests -p preprocess_tests.py -v` | 9 PASS |
| `npm ci` | PASS after dependency patch; 0 audit vulnerabilities |
| `npm run test` | 34/34 PASS in 8 files |
| `npm run typecheck` | PASS |
| `npm run lint` | PASS |
| `npm run build` | PASS; 85 modules |
| `npm audit` | PASS; 0 vulnerabilities after patch |
| `.venv/Scripts/python.exe experiments/benchmarks/validate_road.py` | PASS; 180 equal-cost pairs, zero heuristic edge violations |
| `.venv/Scripts/python.exe experiments/benchmarks/validate_supporting.py` | PASS; 20 cache-equivalent pairs, 20 ranking pairs, 12 sensor episodes |
| `py -3.14 experiments/benchmarks/validate_final_selection.py` | PASS; 10 static source-map configurations and clear endpoints |
| `.venv/Scripts/python.exe experiments/benchmarks/validate_final_benchmark.py` | PASS; 351 decisions, 21 eligible pairs, 14 figures, 69 local document links |
| `py -3.14 report/hcmut-project/scripts/validate_report.py` | PASS; 21 pages, references on physical page 21, 53 frozen LNCS source files, 56 benchmark hashes, 8 figures and 3 tables preserved |
| `py -3.14 report/springer-lncs/scripts/validate_pdf_text.py` | PASS; 19 pages, Unicode extraction, author/header and table-placement checks |
| README local-link existence check | PASS; 32 local links |
| `git diff --check` | PASS |

Validation hiccups were resolved without changing tests: the application venv lacks `pypdf`, so report validation used the existing Python 3.14 environment. One dependency reinstall overlapped a running frontend test process, causing Windows EPERM and missing-module failures; after that process ended, a clean `npm ci` and the full frontend sequence were rerun successfully. These failed attempts are not counted as passing runs. No tests or acceptance gates were weakened.

## Artifact preservation

Both PDFs were compared byte-for-byte against the approved `df8607a` Git blobs; no rebuild was performed.

| Artifact | SHA-256 |
| --- | --- |
| `report/hcmut-project/report.pdf` | `26a9d6909a9e9d7ef1a94ce3d63cb4db716b6248eca5e1ea33887d0f7dd20c22` |
| `report/springer-lncs/report.pdf` | `6eaff7f6fd6059632265808ba3e40bd896cfb57576894f2b98d123fd13b2ab52` |

Both `main.tex` entry points, section sources, bibliography, figures, templates, metadata and build scripts remain tracked. The final benchmark manifest verifies all 56 frozen artifact hashes. External authors checkout remains clean and unchanged at `8bbbfb81cbe76c9f559f15f5c68f1eb4998915d8`; it was neither deleted nor committed.

## Verified capabilities and remaining limitations

- Road search uses identical graph/cost inputs for A* and Dijkstra; 180/180 frozen pairs agree. The median paired expansion reduction is 76% and search-time ratio 0.338. These are local frozen search results, not a universal speed guarantee.
- Robot navigation preserves limited sensing, discovered-map planning, parent-aware recovery, C++ A* and reversed-entry fallback. The full deterministic regression suite passes; unknown-environment global optimality and universal exploration completeness are not claimed.
- The shared-state robot comparison covers 21 eligible local planned-path pairs from 351 recorded decisions. Primary obstacle-interior validity is 21/21 for both; strict boundary-free validity differs (ASP 15/21, A* 21/21). Point-path results do not establish finite-radius motion safety.
- The 48-case direct end-to-end comparison remains blocked by unresolved original source motion/footprint compatibility. No blocked comparison was executed and no measurements were regenerated during integration.
- The authors repository supplies no redistribution license. External source/maps and locally supplied research PDFs are not newly bundled. Existing attributed templates, style files, original provided A* reference and OSM-derived data are preserved.
- The existing Python deprecation warning remains. Full frozen-source validation requires the separate pinned authors checkout and report tools; application startup does not.

The final published SHA is the documentation/security commit visible at main after fast-forward; `git log -1 main` and `git ls-remote origin refs/heads/main` verify local/remote identity. Branches are retained for provenance.
