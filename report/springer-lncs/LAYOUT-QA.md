# Layout QA

Final writing-revision build: 2026-10-09, branch `codex/springer-lncs-writing-refinement`, based on `861e120`; pdfTeX 1.40.28 (MiKTeX), official unmodified LNCS v2.26 (25-Feb-2025), `splncs04`. **18 physical pages total**, unchanged from the completed report. Main content occupies pages1–17 and the opening of18; references begin on18. The body remains above the earlier approximate12–16-page target. The nine section sources are slightly shorter after revision. No margins/fonts were compressed to meet a number.

Class content area: 12.2×19.3 cm, one column, standard10-point body and class-defined abstract/caption/reference fonts. PDF media: 612×792 points (Letter default of this class/article configuration). Natural-bottom alignment uses `raggedbottom` to avoid stretching paragraphs around floats; it changes neither margins nor fonts. Algorithm1 is anchored after its explanatory paragraphs using the standard algorithm float package. No forced page breaks, manual negative spacing, resized tables, or decorative graphics.

## Final checks

- All18 final pages rendered with Poppler at120dpi; every page inspected in labeled contact sheets, with full-resolution checks of the algorithm, heuristic/return derivation, and references. Unchanged earlier-page renders were reviewed during the final wording iterations; the final complete contact set was reviewed again.
- Title, explicit author/affiliation fields,165-word abstract and six keywords are readable.
- All9 sections,8 figures,3 tables,1 algorithm,5 equations, and9 references are numbered and cited consistently.
- No clipping, chart-label or legend overlap, diagram-box overflow, missing glyph, blank page, broken citation, placeholder body text, or table overflow was found.
- Final log has **zero** overfull/underfull boxes, package/LaTeX warnings, undefined citations or references. BibTeX resolved all9 substantively used keys.
- Vector PDFs are used for all report figures, with fonts embedded; plot labels are authored at LNCS-width scale. The observed-space illustration never displays hidden ground truth.
- Final body fonts use CM-Super Type1 outlines for the existing T1 Computer Modern family, with pdfTeX glyph-to-Unicode mappings. All23 used font resources have ToUnicode maps; none is Type3. Both pypdf and Poppler find representative ligature words, the accented author name, and mathematical symbols without replacement/control characters. This corrects the original committed PDF's reproducible extraction defect. Whitespace and line-wrap hyphenation remain extractor-dependent.
- The intentional unverified author/affiliation fields in `metadata.tex` must be replaced before academic submission; they are not unresolved LaTeX references or invented identities.

## Page-by-page inspection

| Pages | Inspected content | Finding |
|---|---|---|
|1|Title, metadata, abstract, keywords, opening|Clean; no abstract overflow.|
|2|Problem motivation, f=g+h, consistency|Equations and references legible; standard heading hierarchy.|
|3|Representation/replanning, observation/exploration literature|Clean text and citations; theme-based synthesis.|
|4|Bundle literature, road formulation, partially observed space|Readable equations, no unsupported generic convergence statement.|
|5|Online-length formula, recovery semantics, architecture introduction|Clean mathematical subscripts and paragraph flow.|
|6|Architecture figure, engine and road representation|Final shortened labels fit all boxes; arrows/connectors legible.|
|7|Road-map figure, sensor/ancestry implementation|Three routes distinguishable; coordinates and legend clear.|
|8|C++ structures/update explanation, Algorithm1|Algorithm follows section introduction; all20 numbered lines fit.|
|9|Heuristics, counters, return bound, methodology opening|No cut-off symbols or formula overflow.|
|10|Environment, paired road timing, source-motion, local requests and eligibility|Source identifiers and numbers readable; protocol qualifications retained.|
|11|Eligibility table, geometry/timing metrics, online study protocol|Table captions above tables; columns fit without resizing.|
|12|Road table, paired expansion/time figure, road results|Both panel axes/legends visible; table units and paired definitions clear.|
|13|Observed robot map, mixed lengths, strict-validity discussion begins|Visible-only geometry clearly labeled; path/target markers legible.|
|14|Cohort table, all-pair lengths, clearance and runtime discussion|Boundary-contact markers preserved; no label overlap.|
|15|Validity chart, runtime interpretation, online ranking/cache/return results|Legend above chart; no numbers or bars covered.|
|16|Runtime chart, recovery interpretation, model/guarantee limitations|Legend outside data; log axis clear; paragraphs fit.|
|17|Cache/return figure, comparison/sampling limits, historical regression record, conclusion opening|All four return pairs and20 cache points readable; no false safety equivalence.|
|18|Conclusion and complete reference list|All9 references fit on the same final page; DOIs/URL wrap inside content width.|

The final PDF and sources are the deliverables. Ignored `qa-render` images are reproducible review intermediates. Page count and bibliographic/figure counts are machine-recorded in `validation.json`.
