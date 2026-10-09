"""Read-only benchmark checks, plus report completeness and build checks."""
import csv
import hashlib
import json
from pathlib import Path
import re
import statistics as st
import subprocess
import sys
from pypdf import PdfReader

REPORT=Path(__file__).resolve().parents[1]
ROOT=REPORT.parents[1]
DATA=ROOT/'experiments/benchmarks'
BASE='04c48468c6b6b4f6512be925383614267fa7ca32'

def rows(name):
    with (DATA/name).open(newline='',encoding='utf-8') as f: return list(csv.DictReader(f))

def main():
    subprocess.run([sys.executable,str(DATA/'validate_final_benchmark.py')],check=True)
    manifest=json.loads((DATA/'benchmark-final-manifest.json').read_text())
    for name,digest in manifest['artifact_sha256'].items():
        assert hashlib.sha256((DATA/name).read_bytes()).hexdigest()==digest,name
    changed=subprocess.check_output(['git','diff',BASE,'--name-only'],cwd=ROOT,text=True).splitlines()
    assert all(p.startswith('report/springer-lncs/') for p in changed),changed
    paired={}
    for r in rows('road-astar-dijkstra.csv'): paired.setdefault(r['pair_id'],{})[r['algorithm']]=r
    assert len(paired)==180
    ratios=[];reductions=[]
    for p in paired.values():
        a,d=p['astar'],p['dijkstra']
        assert abs(float(a['cost_m'])-float(d['cost_m']))<1e-6
        ratios.append(float(a['median_search_us'])/float(d['median_search_us']))
        reductions.append(1-int(a['expanded_nodes'])/int(d['expanded_nodes']))
    assert round(st.median(ratios),3)==.338
    assert round(100*st.median(reductions),1)==76.0
    r=rows('robot-local-final-paired.csv')
    delta=[float(p['astar_planned_length'])-float(p['asp_planned_length']) for p in r]
    assert len(r)==21 and (sum(d>1e-7 for d in delta),sum(d<-1e-7 for d in delta))==(9,10)
    assert round(st.median(delta),3)==0 and round(st.mean(delta),3)==2.981
    maintex=(REPORT/'main.tex').read_text()
    abstract=maintex.split(r'\begin{abstract}')[1].split(r'\keywords')[0]
    abstractwords=len(abstract.split())
    assert 150<=abstractwords<=200,abstractwords
    sections=sorted((REPORT/'sections').glob('*.tex'))
    assert len(sections)==9
    alltex=maintex+'\n'+'\n'.join(p.read_text() for p in sections)
    cited=set()
    for group in re.findall(r'\\cite\{([^}]+)\}',alltex): cited.update(group.split(','))
    keys=set(re.findall(r'@\w+\{([^,]+)',(REPORT/'references.bib').read_text()))
    assert cited==keys and len(keys)==9,(cited,keys)
    log=(REPORT/'report.log').read_text(errors='replace')
    assert not re.search(r'Overfull|Underfull|undefined|LaTeX Warning|Package .* Warning',log)
    pdf=PdfReader(REPORT/'report.pdf')
    texts=[p.extract_text() or '' for p in pdf.pages]
    assert all(t.strip() for t in texts)
    assert len(re.findall(r'\\begin\{figure\}',alltex))==8
    assert len(list((REPORT/'figures').glob('*.pdf')))==8
    # This unmodified class/article configuration defaults to US Letter media.
    # LNCS fixes the content area at 12.2 x 19.3 cm independently of media size.
    assert all(abs(float(p.mediabox.width)-612)<1 and abs(float(p.mediabox.height)-792)<1 for p in pdf.pages)
    result={'status':'PASS','baseline':BASE,'total_pages':len(pdf.pages),
            'references_start_page':next(i+1 for i,t in enumerate(texts) if 'References' in t),
            'abstract_words_whitespace':abstractwords,'figures':8,'tables':3,'algorithms':1,
            'bibliography_entries':len(keys),'road_pairs':180,'robot_snapshots':351,
            'eligible_robot_pairs':21,'frozen_benchmark_hashes_checked':len(manifest['artifact_sha256']),
            'visual_qa':'See LAYOUT-QA.md; automated checks do not substitute for page inspection.'}
    (REPORT/'validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
