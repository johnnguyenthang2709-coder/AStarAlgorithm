# HCMUT A* university project report

This is a separate, self-contained format conversion of the verified Springer LNCS manuscript at **`faaeb2c`**, derived on branch `codex/hcmut-project-report`. The original `../springer-lncs/` project remains unchanged. The benchmark revision is `04c48468c6b6b4f6512be925383614267fa7ca32`.

## Build

From the repository root in PowerShell:

```powershell
& report/hcmut-project/scripts/build.ps1
py -3.14 report/hcmut-project/scripts/validate_report.py
py -3.14 report/hcmut-project/scripts/render_qa.py
```

The build script runs pdfLaTeX, BibTeX, and two further pdfLaTeX passes. Its `-TexBin` parameter accepts another MiKTeX executable directory. Alternatively, from this directory:

```text
pdflatex -interaction=nonstopmode -halt-on-error -jobname=report main.tex
bibtex report
pdflatex -interaction=nonstopmode -halt-on-error -jobname=report main.tex
pdflatex -interaction=nonstopmode -halt-on-error -jobname=report main.tex
```

Compilation uses only relative asset paths and standard TeX packages; it does not depend on the LNCS source directory. Python validators require `pypdf`; rendering also requires Pillow and Poppler `pdftoppm`/`pdftotext` on PATH. Validation intentionally requires the repository, frozen source revision, benchmark artifacts, and pinned external authors' checkout. Rendering/build products are ignored except the final PDF, validation record, and cover preview.

## Presentation

A4, `article`, 12pt Computer Modern serif, T1 outlines with Unicode mappings, one column, exactly 2.5 cm margins, 1.15 body line spacing. The contents page uses conventional single spacing at unchanged font size. Page numbers are omitted from the cover, Roman for front matter, and Arabic from Introduction. Nine numbered primary sections retain the complete scientific content. Full-width figures keep their aspect ratios. Float-only pages are top aligned to avoid excessive gaps.

Numeric citations retain the supplied `splncs04.bst`, avoiding changes to verified bibliography fields or citation ordering. This university document does **not** use the Springer document class or title-page layout. The supplied bibliography style retains its original license notice.

## Verified and optional metadata

`metadata.tex` contains Nguyen Hoang Thang, the university names, the supplied Faculty of Applied Science, and lecturer Phan Thanh An. Course, student ID, class, and submission date are unset and do not print. They are optional editable fields, not assertions that the course requires them. No supervisor, coauthor, email, ORCID, signed declaration, or copyright grant has been added.

The initial repository contained no HCMUT logo or actual Calculus sample. The author subsequently supplied the university PNG, lecturer, faculty, and a sample-cover screenshot. The cover now uses that supplied logo proportionally, with white margins trimmed in LaTeX; see `assets/README.md`. The A* topic, single-author scope, and verified scientific content remain intact; unrelated Calculus/group metadata from the example is not imported.

## Scientific preservation

All nine source sections, the abstract, equations, pseudocode, captions, limitations, and citations are retained. Primary heading names and float placement are adapted. Three appended paragraphs explain report organization, the application interface, and cautious future improvements; no experiment, numerical claim, algorithm, or guarantee is added. Eight figures and the bibliography/style are copied byte-for-byte; table content is identical except placement controls. The reviewed literature matrix and inventory are copied unchanged as supplementary documentation.

`scripts/validate_report.py` checks source Git-blob identity, scientific content in sequence, font embedding/Unicode, A4/text dimensions, contents page references, and all 56 frozen benchmark hashes. It also runs the existing frozen benchmark validator. The legacy LNCS validator was run successfully before committing this separate project; its branch-scope guard allows only LNCS changes and is not intended as a validator for a branch adding another report directory. Its source is preserved. Use the new validator for repeatable checks on this branch.

See `QA.md` and `validation.json` for the verified conversion record. No production code or benchmark artifacts were changed, and no production regression rerun was necessary.
