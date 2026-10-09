"""Check font mappings and searchable text with two independent extractors.

Reads the original report from Git without replacing any working-tree artifact.
Writes only report-local diagnostics; requires pypdf and Poppler pdftotext.
"""
from io import BytesIO
import json
from pathlib import Path
import subprocess
import tempfile
import unicodedata

from pypdf import PdfReader

REPORT = Path(__file__).resolve().parents[1]
ROOT = REPORT.parents[1]
ORIGINAL = "861e1200083a1099c1b50e1c69ad67a34f68df5b"


def invalid_characters(text):
    return sorted({f"U+{ord(c):04X}" for c in text
                   if c == "\ufffd" or (ord(c) < 32 and c not in "\n\r\t\f")})


def check_pdf_text():
    original_bytes = subprocess.check_output(
        ["git", "show", f"{ORIGINAL}:report/springer-lncs/report.pdf"], cwd=ROOT)
    old_text = "\n".join(p.extract_text() or ""
                         for p in PdfReader(BytesIO(original_bytes)).pages)
    reader = PdfReader(REPORT / "report.pdf")
    texts = [p.extract_text() or "" for p in reader.pages]
    extracted = "\n".join(texts)
    assert all(t.strip() for t in texts), "An empty searchable page was found"
    fonts = {}
    for page in reader.pages:
        for ref in page["/Resources"].get("/Font", {}).get_object().values():
            font = ref.get_object()
            name = str(font.get("/BaseFont", ref))
            assert font.get("/Subtype") != "/Type3", name
            assert "/ToUnicode" in font, name
            fonts[name] = str(font.get("/Subtype"))
    with tempfile.TemporaryDirectory(prefix="astar-report-text-") as tmp:
        poppler = Path(tmp) / "poppler.txt"
        subprocess.run(["pdftotext", "-enc", "UTF-8", "-layout",
                        str(REPORT / "report.pdf"), str(poppler)], check=True)
        independent = poppler.read_text(encoding="utf-8")
    checked_terms = ["Nguyen Hoang Thang", "verified", "different", "effort",
                     "configuration", "P\u00e9rez", "\u03b5", "\u2264", "\u2208", "\u2217"]
    for name, text in [("pypdf", extracted), ("Poppler", independent)]:
        assert not invalid_characters(text), (name, invalid_characters(text))
        normalized = unicodedata.normalize("NFKC", text)
        for term in checked_terms:
            assert term in normalized, (name, term)
    expected_metadata = (
        "% Author and affiliation verified by the author; no additional metadata supplied.\n"
        "\\newcommand{\\ReportAuthor}{Nguyen Hoang Thang}\n"
        "\\newcommand{\\ReportRunningAuthor}{Nguyen Hoang Thang}\n"
        "\\newcommand{\\ReportAffiliation}{Faculty of Computer Science and Engineering\\\\\n"
        "University of Technology\\\\\n"
        "Vietnam National University, Ho Chi Minh City}\n"
    )
    assert (REPORT / "metadata.tex").read_text(encoding="utf-8") == expected_metadata
    for term in ["Nguyen Hoang Thang", "Faculty of Computer Science and Engineering",
                 "University of Technology", "Vietnam National University, Ho Chi Minh City"]:
        assert term in texts[0], ("title page", term)
        assert term in independent.split("\f")[0], ("Poppler title page", term)
    assert "Author name to be supplied" not in extracted
    assert "Affiliation to be supplied" not in extracted
    # Standard runningheads places the author on even-numbered pages.
    for index in range(1, len(texts), 2):
        assert "Nguyen Hoang Thang" in texts[index].splitlines()[0], index + 1
    for name in ["references.bib", "llncs.cls", "splncs04.bst"]:
        original = subprocess.check_output(
            ["git", "show", f"{ORIGINAL}:report/springer-lncs/{name}"], cwd=ROOT)
        assert (REPORT / name).read_bytes() == original, name
    for folder in ["figures", "tables"]:
        for path in sorted((REPORT / folder).iterdir()):
            if not path.is_file():
                continue
            relative = path.relative_to(ROOT).as_posix()
            original = subprocess.check_output(
                ["git", "show", f"{ORIGINAL}:{relative}"], cwd=ROOT)
            assert path.read_bytes() == original, relative
    result = {
        "status": "PASS", "original_report_commit": ORIGINAL,
        "pages_checked_with_both_extractors": len(texts),
        "original_pypdf_invalid_character_codes": invalid_characters(old_text),
        "revised_invalid_character_codes": [],
        "font_resources_with_Unicode_maps": len(fonts),
        "type3_font_resources": 0, "checked_search_terms": checked_terms,
        "unchanged_assets": "bibliography, official class/style, all figures/tables",
        "verified_metadata": "Nguyen Hoang Thang; supplied three-line affiliation",
        "title_page_and_even_page_author_headers": "PASS",
        "extraction_limit": "Reading-order whitespace and line-wrap hyphens remain extractor-dependent; math is not a structured equation export.",
    }
    (REPORT / "pdf-text-validation.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(check_pdf_text(), indent=2, ensure_ascii=True))
