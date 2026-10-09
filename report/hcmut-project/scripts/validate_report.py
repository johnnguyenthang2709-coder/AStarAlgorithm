"""Read-only scientific equivalence and format checks; report-local diagnostics only."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unicodedata
import xml.etree.ElementTree as ET

from pypdf import PdfReader

REPORT = Path(__file__).resolve().parents[1]
ROOT = REPORT.parents[1]
SOURCE = ROOT / 'report/springer-lncs'
REVISION = 'faaeb2c'
BENCHMARK = ROOT / 'experiments/benchmarks'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(text):
    text = text.replace(r"\begingroup\predisplaypenalty=0", "").replace(r"\endgroup", "")
    # samepage groups affect pagination only; retain all enclosed science text.
    text = re.sub(r"\\(?:begin|end)\{samepage\}", "", text)
    text = re.sub(r'\\begin\{(figure|table)\}\[(?:t|H|!?htbp)\]',
                  r'\\begin{\1}[htbp]', text)
    text = re.sub(r"\\par(?=\s|$)", "", text)
    return ' '.join(text.split())


def main():
    # The scientific manuscript is frozen byte-for-byte, including its PDF.
    tracked = subprocess.check_output(
        ['git', 'ls-tree', '-r', '--name-only', REVISION, 'report/springer-lncs'],
        cwd=ROOT, text=True).splitlines()
    for name in tracked:
        old = subprocess.check_output(['git', 'rev-parse', f'{REVISION}:{name}'], cwd=ROOT).strip()
        current = subprocess.check_output(['git', 'hash-object', '--path', name, name], cwd=ROOT).strip()
        assert current == old, name
    sections = sorted((SOURCE / 'sections').glob('*.tex'))
    assert len(sections) == 9
    equivalence = []
    for source in sections:
        # Primary heading names adapt to the brief; every source paragraph,
        # equation, citation and pseudocode line must remain in sequence.
        original = canonical(source.read_text().split('\n', 1)[1])
        converted = canonical((REPORT / 'sections' / source.name).read_text().split('\n', 1)[1])
        assert converted.startswith(original), source.name
        equivalence.append(source.name)
    source_main = (SOURCE / 'main.tex').read_text()
    abstract = source_main.split(r'\begin{abstract}')[1].split(r'\keywords')[0].strip()
    assert canonical(abstract) in canonical((REPORT / 'sections/00-abstract.tex').read_text())
    for name in ('references.bib', 'splncs04.bst'):
        assert (SOURCE / name).read_bytes() == (REPORT / name).read_bytes(), name
    figures = sorted((SOURCE / 'figures').glob('*.pdf'))
    assert len(figures) == 8
    for figure in figures:
        assert figure.read_bytes() == (REPORT / 'figures' / figure.name).read_bytes()
    for table in (SOURCE / 'tables').glob('*.tex'):
        assert canonical(table.read_text()) == canonical((REPORT / 'tables' / table.name).read_text())
    manifest = json.loads((BENCHMARK / 'benchmark-final-manifest.json').read_text())
    for name, digest in manifest['artifact_sha256'].items():
        assert sha((BENCHMARK / name).read_bytes()) == digest, name
    subprocess.run([sys.executable, str(BENCHMARK / 'validate_final_benchmark.py')], check=True)
    maintex = (REPORT / 'main.tex').read_text()
    assert r'\documentclass[a4paper,12pt,oneside]{article}' in maintex
    assert r'\usepackage[margin=2.5cm]{geometry}' in maintex
    assert r'\setstretch{1.15}' in maintex
    assert not any(x in maintex for x in ('twocolumn', 'multicol', 'titlesec'))
    alltex = maintex + '\n'.join(p.read_text() for p in (REPORT / 'sections').glob('*.tex'))
    keys = set(re.findall(r'@\w+\{([^,]+)', (REPORT / 'references.bib').read_text()))
    cites = set()
    for group in re.findall(r'\\cite\{([^}]+)\}', alltex):
        cites.update(group.split(','))
    assert cites == keys and len(keys) == 9
    assert alltex.count(r'\begin{figure}') == 8
    assert alltex.count(r'\begin{algorithm}') == 1
    log = (REPORT / 'report.log').read_text(errors='replace')
    assert not re.search(r'Overfull|Underfull|undefined|LaTeX.*Warning|Package .* Warning|duplicate ignored', log)
    metrics = re.search(r'REPORT-FORMAT: font=(\d+)pt; textwidth=([\d.]+)pt; textheight=([\d.]+)pt', log)
    assert metrics and metrics[1] == '12'
    assert abs(float(metrics[2]) - 160 / 25.4 * 72.27) < 0.02
    assert abs(float(metrics[3]) - 247 / 25.4 * 72.27) < 0.02
    pdf = PdfReader(REPORT / 'report.pdf')
    texts = [p.extract_text() or '' for p in pdf.pages]
    assert all(t.strip() for t in texts)
    assert all(abs(float(p.mediabox.width) - 595.276) < 0.1 and
               abs(float(p.mediabox.height) - 841.89) < 0.1 for p in pdf.pages)
    for word in ('Nguyễn Đức Hòa', 'Nguyễn Hoàng Thắng', 'PROJECT REPORT', 'A* SEARCH ALGORITHM',
                 'HCMC UNIVERSITY OF TECHNOLOGY',
                 'UNIVERSITY OF TECHNOLOGY', 'FACULTY OF APPLIED SCIENCE', 'Lecturer: Phan Thanh An'):
        assert ''.join(word.split()) in ''.join(texts[0].split()), word
    assert (REPORT / 'assets/hcmut-logo.png').exists()
    assert 'tobesupplied' not in ''.join(texts[0].split())
    intro = next(i for i, text in enumerate(texts) if re.search(r'1\s+Introduction', text)
                 and 'Contents' not in text and 'Abstract' not in text)
    assert pdf.page_labels[intro] == '1', pdf.page_labels
    assert pdf.page_labels[1] == 'i'
    toc = (REPORT / 'report.toc').read_text()
    assert len(re.findall(r'\\contentsline \{section\}', toc)) == 11
    for level, number, title, page in re.findall(
            r'\\contentsline \{(section|subsection)\}\{\\numberline \{([^}]+)\}([^}]+)\}\{([^}]+)\}', toc):
        physical = intro + int(page) - 1
        assert title in ' '.join(texts[physical].split()), (number, title, page)
    assert any('References' in text for text in texts[intro:])
    assert '[9]' in texts[-1]
    font_count = 0
    for page in pdf.pages:
        for ref in page['/Resources'].get('/Font', {}).get_object().values():
            font = ref.get_object()
            assert font.get('/Subtype') != '/Type3'
            assert '/ToUnicode' in font
            descriptor = font.get('/FontDescriptor')
            if descriptor:
                descriptor = descriptor.get_object()
                assert any(x in descriptor for x in ('/FontFile', '/FontFile2', '/FontFile3'))
            font_count += 1
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / 'text.txt'
        subprocess.run(['pdftotext', '-enc', 'UTF-8', '-layout', str(REPORT / 'report.pdf'), str(out)], check=True)
        poppler = out.read_text(encoding='utf-8')
        bbox = Path(tmp) / 'bbox.html'
        subprocess.run(['pdftotext', '-bbox-layout', str(REPORT / 'report.pdf'), str(bbox)], check=True)
        ns = {'x': 'http://www.w3.org/1999/xhtml'}
        cover = ET.parse(bbox).getroot().find('.//x:page', ns)
        words = cover.findall('.//x:word', ns)
        header = next(w for w in words if w.text == 'Name')
        table_words = [w for w in words if float(w.attrib['yMin']) >= float(header.attrib['yMin'])]
        table_center = (min(float(w.attrib['xMin']) for w in table_words) +
                        max(float(w.attrib['xMax']) for w in table_words)) / 2
        table_center_offset = table_center - float(cover.attrib['width']) / 2
        assert abs(table_center_offset) < 1.0, table_center_offset
    reference_page = int(re.search(r'\\contentsline \{section\}\{References\}\{(\d+)\}', toc)[1])
    assert texts[intro + reference_page - 1].startswith('References')
    rows = ('Nguyễn Đức Hòa CC06 2652600', 'Phạm Văn Bảo Phong CC06 2652465',
            'Nguyễn Bá Hoàng CC06 2651237', 'Nguyễn Hoàng Thắng CC06 2550216',
            'Nguyễn Hưng Phát CC06 2651590')
    compact_cover = ''.join(texts[0].split())
    for row in rows:
        assert ''.join(row.split()) in compact_cover, row
    for text in ('\n'.join(texts), poppler):
        assert not any(c == '\ufffd' or (ord(c) < 32 and c not in '\n\r\t\f') for c in text)
        normalized = unicodedata.normalize('NFKC', text)
        for term in ('Nguyễn Đức Hòa', 'Phạm Văn Bảo Phong', 'Nguyễn Bá Hoàng', 'Nguyễn Hoàng Thắng', 'Nguyễn Hưng Phát', '2652600', '2652465', '2651237', '2550216', '2651590', 'CC06', 'configuration', 'verified', 'Pérez', 'ε', '≤', '∈'):
            assert term in normalized, term
    result = dict(status='PASS', source_revision=REVISION,
                  frozen_source_files_unchanged=len(tracked), source_sections_preserved=equivalence,
                  abstract_preserved=True, figures_byte_identical=8, tables_content_identical=3,
                  references_byte_identical=9, algorithms=1, total_pages=len(pdf.pages),
                  cover_table_center_offset_pt=round(table_center_offset, 6),
                  reference_physical_page=intro + reference_page,
                  introduction_physical_page=intro+1, introduction_page_label='1',
                  toc_section_entries=11, toc_numbered_entries_checked=True,
                  format='A4 article, 12pt, one column, 2.5cm margins, 1.15 line spacing',
                  unicode_extractors=['pypdf', 'Poppler'], mapped_font_instances=font_count,
                  frozen_benchmark_hashes_checked=len(manifest['artifact_sha256']),
                  visual_qa='See QA.md; automated checks do not replace visual inspection.')
    (REPORT / 'validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
