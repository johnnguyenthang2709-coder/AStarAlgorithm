"""Render every manuscript page and create labeled contact sheets for visual QA."""
from pathlib import Path
import subprocess
from PIL import Image, ImageDraw
REPORT=Path(__file__).resolve().parents[1]
OUT=REPORT/'qa-render'
OUT.mkdir(exist_ok=True)
subprocess.run(['pdftoppm','-r','120','-png',str(REPORT/'report.pdf'),str(OUT/'page')],check=True)
pages=sorted(OUT.glob('page-*.png'))
# Only current PDF pages; earlier longer builds may leave extra numbered images.
from pypdf import PdfReader
pages=pages[:len(PdfReader(REPORT/'report.pdf').pages)]
for offset in range(0,len(pages),4):
    sheet=Image.new('RGB',(1480,2140),'#ddd')
    draw=ImageDraw.Draw(sheet)
    for j,path in enumerate(pages[offset:offset+4]):
        im=Image.open(path).convert('RGB');im.thumbnail((730,1030))
        x=(j%2)*740+(740-im.width)//2;y=(j//2)*1070+28
        sheet.paste(im,(x,y));draw.text((x,y-20),f'Page {offset+j+1}',fill='black')
    sheet.save(OUT/f'contact-{offset+1:02d}.png')
print(f'Rendered {len(pages)} pages at 120 dpi; contact sheets in {OUT}')
