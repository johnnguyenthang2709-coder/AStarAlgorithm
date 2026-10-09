"""Report-only figures from frozen measurements. Never writes benchmark files."""
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
import subprocess
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.collections import LineCollection

REPORT = Path(__file__).resolve().parents[1]
ROOT = REPORT.parents[1]
DATA = ROOT / 'experiments/benchmarks'
OUT = REPORT / 'figures'
BLUE, ORANGE, PURPLE = '#24677c', '#b45c25', '#76518b'
plt.rcParams.update({'font.size': 9, 'axes.titlesize': 9, 'axes.labelsize': 9,
                    'legend.fontsize': 8, 'axes.spines.top': False,
                    'axes.spines.right': False, 'pdf.fonttype': 42})

def rows(name):
    with (DATA / name).open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def save(fig, name):
    fig.tight_layout(pad=.5)
    fig.savefig(OUT / f'{name}.pdf', metadata={'CreationDate': None, 'ModDate': None})
    fig.savefig(OUT / f'{name}.png', dpi=180)
    plt.close(fig)

def architecture():
    fig, ax = plt.subplots(figsize=(4.8, 2.75))
    ax.set(xlim=(0, 10), ylim=(-.2, 6)); ax.axis('off')
    def box(x,y,w,h,text):
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.08',
                     facecolor='#eef3f5', edgecolor=BLUE, linewidth=.8))
        ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=8)
    box(.2,4.65,3.8,1,'React / TypeScript\nRoutes, sensing, playback')
    box(.2,3.15,3.8,.9,'FastAPI\nRoad / robot requests')
    box(.2,1.25,3.8,1.25,'Python robot controller\nSensing, observed map, targets\nAncestry and locked execution')
    box(5.3,3.15,4.3,.9,'C++ adapters via pybind11\nRoad / grid / Euclidean links')
    box(5.3,1.25,4.3,1.25,'Shared C++17 A* core\nHeap, scores, parents, trace\nDijkstra uses h = 0')
    box(.2,.05,3.8,.6,'Ground truth\nSensor / collision checks')
    box(5.3,.05,4.3,.6,'Known directed road graph')
    def arrow(a,b,label=None):
        ax.annotate('',xy=b,xytext=a,arrowprops={'arrowstyle':'->','color':'#555','lw':.9})
        if label: ax.text((a[0]+b[0])/2,(a[1]+b[1])/2+.15,label,ha='center',fontsize=7)
    arrow((2.1,4.65),(2.1,4.05)); arrow((4,3.6),(5.25,3.6))
    arrow((2.1,3.15),(2.1,2.55)); arrow((4,2),(5.25,3.3),'links')
    arrow((7.45,3.15),(7.45,2.55)); arrow((2.1,.65),(2.1,1.15))
    arrow((7.45,.65),(7.45,1.15))
    save(fig,'architecture')

def road():
    paired=defaultdict(dict)
    for r in rows('road-astar-dijkstra.csv'): paired[int(r['pair_id'])][r['algorithm']]=r
    fig, axes = plt.subplots(1,2,figsize=(4.8,2.6))
    for ax,field,label in zip(axes,['expanded_nodes','median_search_us'],['Expanded nodes','Search time (µs)']):
        vals=[]
        for s,c in zip(['short','medium','long'],[BLUE,ORANGE,PURPLE]):
            p=[x for x in paired.values() if x['astar']['stratum']==s]
            dx=[float(x['dijkstra'][field]) for x in p]; ay=[float(x['astar'][field]) for x in p]
            ax.scatter(dx,ay,s=9,color=c,alpha=.7,label=s); vals+=dx+ay
        b=max(vals)*1.04
        ax.plot([0,b],[0,b],'--',color='#555',lw=.7)
        ax.set(xlim=(0,b),ylim=(0,b),xlabel='Dijkstra',ylabel='A*',title=label)
    axes[0].legend(frameon=False,handletextpad=.3)
    save(fig,'road-effort')
    graph=json.loads((ROOT/'data/road/graph.json').read_text(encoding='utf-8'))
    fig,ax=plt.subplots(figsize=(4.8,2.95))
    ax.add_collection(LineCollection([e['geometry'] for e in graph['edges']],colors='#c9cecf',linewidths=.22))
    code=('import json,sys;sys.path.insert(0,sys.argv[1]);import astar_core;'
          'e=astar_core.RoadEngine(sys.argv[2]);'
          'print(json.dumps(astar_core.road_compare(e,int(sys.argv[3]),int(sys.argv[4]),False)))')
    for idx,col in zip([0,60,120],[BLUE,ORANGE,PURPLE]):
        r=paired[idx]['astar']
        result=json.loads(subprocess.check_output([str(ROOT/'.venv/Scripts/python.exe'),'-c',code,
            str(ROOT/'backend'),str(ROOT/'data/road/graph.json'),r['start'],r['goal']],text=True))
        assert result['same_optimal_cost']
        g=result['astar']['route']['geometry']
        assert abs(result['astar']['route']['cost_m']-float(r['cost_m']))<1e-6
        ax.plot([p['lon'] for p in g],[p['lat'] for p in g],color=col,lw=1.5,label=f"{r['stratum']} (pair {idx})")
        ax.scatter([g[0]['lon'],g[-1]['lon']],[g[0]['lat'],g[-1]['lat']],s=12,color=col)
    ax.autoscale();ax.set_aspect('equal');ax.set(xlabel='Longitude (degrees)',ylabel='Latitude (degrees)')
    ax.ticklabel_format(useOffset=False,style='plain'); ax.legend(frameon=False,loc='upper left')
    save(fig,'roads')

def robot():
    r=rows('robot-local-final-paired.csv')
    fig,ax=plt.subplots(figsize=(4.8,2.65))
    colors=[BLUE]*6+[PURPLE]+[ORANGE]*14
    for i,p in enumerate(r):
        boundary=p['asp_strict_boundary_valid']!='True'
        ax.plot([i+1,i+1],[0,float(p['astar_minus_asp_length'])],color=colors[i],lw=1)
        ax.scatter(i+1,float(p['astar_minus_asp_length']),s=24,
                   facecolor=ORANGE if boundary else 'white',edgecolor=colors[i],marker='o')
    ax.axhline(0,color='#555',lw=.8);ax.axvline(6.5,color='#aaa',lw=.7);ax.axvline(7.5,color='#aaa',lw=.7)
    ax.set(xlabel='Frozen pair index: initial 1–6; held-out 7; prospective 8–21',
           ylabel='A* − ASP length (world units)',xticks=[1,3,6,7,10,15,21])
    save(fig,'robot-length')
    fig,ax=plt.subplots(figsize=(4.8,2.25))
    labels=['Interior-only point','Strict point','Radius 0.5 diagnostic']
    for offset,key,c in [(-.18,'asp',ORANGE),(.18,'astar',BLUE)]:
        fields=['interior_only_valid','strict_boundary_valid','radius_0_5_clearance_valid']
        counts=[sum(p[f'{key}_{f}']=='True' for p in r) for f in fields]
        bars=ax.barh([i+offset for i in range(3)],counts,height=.34,color=c,label='ASP' if key=='asp' else 'A*')
        for b,n in zip(bars,counts): ax.text(n+.15,b.get_y()+b.get_height()/2,str(n),va='center',fontsize=8)
    ax.set(yticks=range(3),yticklabels=labels,xlim=(0,23),xlabel='Valid paths out of 21')
    ax.legend(frameon=False,loc='lower center',bbox_to_anchor=(.5,1.0),ncol=2)
    save(fig,'robot-validity')
    fig,ax=plt.subplots(figsize=(4.8,2.7))
    for fld,label,c in [('asp_core_median_ms','ASP core (Python)',ORANGE),
                        ('astar_build_median_ms','A* graph build (Python)',PURPLE),
                        ('astar_core_median_ms','A* binding/search (C++)',BLUE)]:
        ax.plot(range(1,22),[float(p[fld]) for p in r],marker='o',ms=2.5,lw=.8,label=label,color=c)
    ax.set(yscale='log',xlabel='Frozen pair index',ylabel='Per-state median time (ms)',xticks=[1,6,7,10,15,21])
    ax.legend(frameon=False,fontsize=7.5,loc='lower center',bbox_to_anchor=(.5,1.0),ncol=1)
    save(fig,'robot-runtime')
    # Display only observed geometry from the frozen source state; never load obstacles.
    cohort='robot-local-final-extension';sid='P01-_map_deadend-07'
    snaps=json.loads((DATA/cohort/'robot-local-snapshots.json').read_text())['snapshots']
    s=next(x for x in snaps if x['snapshot_id']==sid)
    plans=json.loads((DATA/cohort/'astar-plans.json').read_text())
    p=next(x for x in plans if x['snapshot_id']==sid)
    # Reuse the independently audited analytic sight adapter for display sampling only.
    sys.path.insert(0,str(DATA))
    from finish_robot_local_benchmark import sight_outline
    fig,ax=plt.subplots(figsize=(4.8,3.1))
    for sight in s['sights']:
        outline=sight_outline(sight,s['sensor_radius'])
        ax.fill([v[0] for v in outline],[v[1] for v in outline],color='#b5d5e0',alpha=.25,lw=0)
        for closed in sight['closed_sights']:
            a,b=closed[:2];ax.plot([a[0],b[0]],[a[1],b[1]],color='#444',lw=1.1)
    for path,label,c in [(s['asp_path'],'ASP',ORANGE),(p['path'],'A*',BLUE)]:
        ax.plot([v[0] for v in path],[v[1] for v in path],lw=1.6,color=c,label=label)
    ax.scatter(*s['start'],marker='o',s=35,color='#222',label='Position',zorder=5)
    ax.scatter(*s['target'],marker='*',s=65,color='#a23535',label='Target',zorder=5)
    ax.set_aspect('equal');ax.set(xlabel='x (world units)',ylabel='y (world units)')
    ax.legend(frameon=False,ncol=2,fontsize=8);save(fig,'robot-observed')

def supporting():
    pairs=defaultdict(dict)
    for r in rows('frontier-cache.csv'): pairs[(r['case'],r['radius'])][r['variant']]=r
    with (ROOT/'docs/bar-indoor-radar-trace.csv').open(newline='') as f: ret=list(csv.DictReader(f))
    assert len(ret)==4 and all(r['fallback']=='False' and r['bound_verified']=='True' for r in ret)
    fig,(ax,bx)=plt.subplots(1,2,figsize=(4.8,2.65))
    x=[float(p['full']['frontier_total_ms']) for p in pairs.values()]
    y=[float(p['cached']['frontier_total_ms']) for p in pairs.values()]
    ax.scatter(x,y,s=12,color=BLUE);b=max(x+y)*1.05;ax.plot([0,b],[0,b],'--',color='#555',lw=.7)
    ax.set(xlabel='Full frontier time (ms)',ylabel='Cached time (ms)',title='20 equivalent pairs')
    bx.bar([i-.18 for i in range(4)],[float(r['entry_length']) for r in ret],.36,color=ORANGE,label='Entry')
    bx.bar([i+.18 for i in range(4)],[float(r['executed_return_length']) for r in ret],.36,color=BLUE,label='Return')
    bx.set(xticks=range(4),xticklabels=[f"{r['branch']}→{r['parent']}" for r in ret],ylabel='Executed length (units)',title='Certified A* returns')
    bx.tick_params(axis='x',labelsize=8);bx.legend(frameon=False,fontsize=8)
    save(fig,'supporting')

if __name__=='__main__':
    OUT.mkdir(exist_ok=True)
    manifest=json.loads((DATA/'benchmark-final-manifest.json').read_text())
    for rel,digest in manifest['artifact_sha256'].items():
        assert hashlib.sha256((DATA/rel).read_bytes()).hexdigest()==digest,rel
    architecture();road();robot();supporting()
    print('Created eight report figures; all frozen benchmark hashes verified.')
