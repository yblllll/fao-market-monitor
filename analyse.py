import json, math, numpy as np, datetime as dt
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from names import by_a3, A3_TO_NUM as A3_NUM
from collections import defaultdict

def mkey(s): return s[:7]                      # 'YYYY-MM'
def midx(k, base):                             # months since base
    y,m=int(k[:4]),int(k[5:7]); by,bm=int(base[:4]),int(base[5:7])
    return (y-by)*12+(m-bm)

def series_array(dps, field, start):
    """dense monthly array from `start` to latest"""
    d={mkey(x['date']): x.get(field) for x in dps if x.get('periodicity')=='monthly' and x.get(field) is not None}
    if not d: return None,None,None
    ks=sorted(d); s=max(start, ks[0]); e=ks[-1]
    n=midx(e,s)+1
    if n<=0: return None,None,None
    arr=[None]*n
    for k,v in d.items():
        i=midx(k,s)
        if 0<=i<n: arr[i]=round(float(v),3)
    return arr, s, e

# ---------- SDG 2.c.1 Indicator of Food Price Anomalies ----------
# Reimplemented to match FAO's own FPMA Tool v4 client implementation, see ipa_fao.py.
from ipa_fao import ipa_series as _ipa_fao

def ipa(arr, start):
    """arr indexed from `start` (YYYY-MM). FAO's routine assumes a January-aligned
    grid, so pad the head, run it, then strip the pad back off."""
    fy = int(start[:4]); pad = int(start[5:7]) - 1
    return _ipa_fao([None]*pad + list(arr), fy)[pad:]

def flag(v):
    if v is None: return 'na'
    if v>=1.0: return 'alert'
    if v>=0.5: return 'warning'
    return 'normal'

def pct(new,old):
    if new is None or old in (None,0): return None
    return round((new/old-1)*100,1)

def last_valid(a):
    for i in range(len(a)-1,-1,-1):
        if a[i] is not None: return i,a[i]
    return None,None

FAM=[('Fertilisers',('fertilizer','urea','potash','phosphate')),
     ('Energy',('crude oil',)),
     ('Dairy',('dairy:',)),('Meat',('meat:','bovine','ovine')),
     ('Cereals',('wheat','maize','rice','barley','sorghum','millet')),
     ('Oilseeds & oils',('soybean','palm','rape','sunflower','coconut','groundnut','fish ','meal','oil')),
     ('Sugar',('sugar',)),
     ('Other agricultural',('tea','banana','cassava','jute','sisal'))]
def fam(name):
    n=name.lower()
    for lab,ks in FAM:
        if any(k in n for k in ks): return lab
    return 'Other agricultural'

# ================= INTERNATIONAL =================
I=json.load(open('data/intl_prices.json'))
intl=[]
for i,m in enumerate(I['meta']):
    dps=I['data'].get(m['uuid'],[])
    arr,s,e=series_array(dps,'price_value_dollar','1996-01')
    if not arr or len(arr)<36: continue
    an=ipa(arr,s)
    li,lv=last_valid(arr)
    rec={'id':i,'n':m['commodity_name'],'o':m['market_name'],'f':fam(m['commodity_name']),
         'u':m['measure_unit_label'],'src':(m['source_name'] or '')[:90],'s':s,'e':e,'v':arr,
         'last':lv,'d':e,
         'mom':pct(lv, arr[li-1] if li and li>=1 else None),
         'yoy':pct(lv, arr[li-12] if li and li>=12 else None),
         'y3':pct(lv, arr[li-36] if li and li>=36 else None),
         'ipa':an[li] if li is not None else None}
    rec['flag']=flag(rec['ipa'])
    intl.append(rec)
print("international series kept:",len(intl))

# ---------- data quality: CPI rebasing breaks the real-price comparison ----------
def cpi_break(dps, months=13):
    """A jump of more than 15% in one month in the implied deflator (nominal/real)
    is a rebasing of the national CPI, not inflation. Where that lands inside the
    comparison window the real change is an artefact, so flag it rather than drop it."""
    pts = sorted([x for x in dps if x.get('periodicity')=='monthly'
                  and x.get('price_value') and x.get('price_value_real')], key=lambda x: x['date'])
    if len(pts) < 2: return 0
    tail = pts[-(months+1):]
    prev = None
    for x in tail:
        d = x['price_value']/x['price_value_real']
        if prev and prev > 0 and abs(math.log(d/prev)) > 0.15: return 1
        prev = d
    return 0

# ================= DOMESTIC =================
D=json.load(open('data/domestic_prices.json'))
dom=[]
for m in D['meta']:
    dps=D['data'].get(m['uuid'],[])
    real,s,e=series_array(dps,'price_value_real','2010-01')
    nom,sn,en=series_array(dps,'price_value','2010-01')
    if not real or len(real)<36: continue
    an=ipa(real,s)
    li,lv=last_valid(real)
    ni,nv=last_valid(nom) if nom else (None,None)
    rec={'iso':m.get('iso3'),'c':by_a3(m.get('iso3'), m['country_name'].title()),'st':m['staple'],'n':m['commodity_name'],
         'cur':m.get('currency'),'u':m.get('measure_unit_label'),'pt':m.get('price_type'),
         's':s,'e':e,'v':real,'last':nv,'d':e,
         'yoyR':pct(lv, real[li-12] if li and li>=12 else None),
         'yoyN':pct(nv, nom[ni-12] if nom and ni and ni>=12 else None),
         'ipa':an[li] if li is not None else None}
    rec['flag']=flag(rec['ipa'])
    rec['dq']=cpi_break(dps)
    rec['ipaS']=[None if x is None else round(x,2) for x in an]
    rec['num']=A3_NUM.get((m.get('iso3') or '').upper())
    dom.append(rec)
print("domestic series kept:",len(dom),"| countries:",len({d['c'] for d in dom}))
print("flags:", {f:sum(1 for d in dom if d['flag']==f) for f in ('alert','warning','normal','na')})
print("CPI rebasing inside the 12m window:", sorted({d['c'] for d in dom if d['dq']}))

# ============ PASS-THROUGH: energy -> fertiliser -> grain ============
def find(sub, origin=None):
    for r in intl:
        if sub.lower() in r['n'].lower() and (origin is None or origin.lower() in r['o'].lower()): return r
def aligned(recs, first='2003-01'):
    end=min(r['e'] for r in recs); start=max(max(r['s'] for r in recs), first)
    n=midx(end,start)+1
    cols=[]
    for r in recs:
        off=midx(start,r['s'])
        cols.append([r['v'][off+i] if 0<=off+i<len(r['v']) else None for i in range(n)])
    return start,end,cols
def hac_ols(y,X,L=6):
    """OLS with Newey-West HAC covariance. Returns coefficients and full V."""
    b,*_=np.linalg.lstsq(X,y,rcond=None)
    u=y-X@b; n,k=X.shape
    XtXi=np.linalg.pinv(X.T@X)
    S=(u[:,None]*X).T@(u[:,None]*X)
    for l in range(1,L+1):
        w=1-l/(L+1); g=(u[l:,None]*X[l:]).T@(u[:-l,None]*X[:-l])
        S+=w*(g+g.T)
    V=XtXi@S@XtXi*n/(n-k)
    return b, V

def cum_se(V, idx):
    """SE of a sum of coefficients: sqrt(R'VR), R the selector. Uses covariances."""
    R=np.zeros(V.shape[0]); R[idx]=1.0
    return float(np.sqrt(R@V@R))

brent=find('Crude oil (Brent)'); urea=find('Urea'); dap=find('Diammonium')
grains=[('Wheat (US No.2 HRW)',find('Wheat (US No. 2, Hard Red Winter)')),
        ('Maize (US No.2 Yellow)',find('Maize (US No. 2, Yellow)')),
        ('Rice (Thai 5% broken)',find('Rice (5% broken)','Thailand'))]
trans={'lags':6,'regs':[],
       'spec':'OLS on monthly log differences, 0-6 month lags of Brent crude and Black Sea urea; Newey-West HAC standard errors (6 lags). Cumulative elasticity = sum of lag coefficients, SE from the full HAC covariance matrix.'}
def run_reg(label,g,first,tag):
    recs=[brent,urea,g]
    start,end,cols=aligned(recs,first)
    A=np.array([[np.nan if v is None else v for v in c] for c in cols],dtype=float).T
    ok=~np.isnan(A).any(axis=1); A=A[ok]
    if len(A)<60: return None
    dl=np.diff(np.log(A),axis=0)
    L=6; T=len(dl)-L
    y=dl[L:,2]
    Xc=[np.ones(T)]
    for j in range(L+1): Xc.append(dl[L-j:len(dl)-j,0])
    for j in range(L+1): Xc.append(dl[L-j:len(dl)-j,1])
    X=np.column_stack(Xc)
    b,V=hac_ols(y,X,L=6); nb=L+1
    ie=list(range(1,1+nb)); iff=list(range(1+nb,1+2*nb))
    ce,cf=float(b[ie].sum()),float(b[iff].sum())
    se_e,se_f=cum_se(V,ie),cum_se(V,iff)
    yhat=X@b; r2=1-((y-yhat)**2).sum()/((y-y.mean())**2).sum()
    return {'dep':label,'sample':tag,'n':int(T),'span':f"{start} to {end}",
            'cum_energy':round(ce,3),'se_energy':round(se_e,3),'t_energy':round(ce/se_e,2) if se_e else None,
            'cum_fert':round(cf,3),'se_fert':round(se_f,3),'t_fert':round(cf/se_f,2) if se_f else None,
            'r2':round(float(r2),3),
            'be':[round(float(x),4) for x in b[ie]],'bf':[round(float(x),4) for x in b[iff]]}
for label,g in grains:
    if not g: continue
    for first,tag in [('2003-01','Full sample'),('2019-01','2019 onwards')]:
        r=run_reg(label,g,first,tag)
        if r:
            trans['regs'].append(r)
            print(f"  {label:24} {tag:14} n={r['n']:4} cumE={r['cum_energy']:+.3f} (t={r['t_energy']:+.2f})  cumF={r['cum_fert']:+.3f} (t={r['t_fert']:+.2f})  R2={r['r2']:.3f}")

# ---------- provenance, derived from the data rather than typed by hand ----------
import re as _re, collections as _c
def _clean(x):
    x=_re.sub(r'\s*\(formerly[^)]*\)','',x or '')
    return _re.sub(r'\s+',' ',x).strip(' ;.')
_pi=_c.Counter()
for m in I['meta']:
    for part in _re.split(r'\s*;\s*|\s+via\s+', m.get('source_name') or ''):
        q=_clean(part)
        if q and len(q)>2: _pi[q]+=1
_pd=_c.Counter(_clean(m.get('source_name')) for m in D['meta'] if _clean(m.get('source_name')))
providers={'intl':[[k,v] for k,v in _pi.most_common(18)],
           'dom':[[k,v] for k,v in _pd.most_common(12)],
           'domTotal':len(_pd)}

payload={'generated':dt.date.today().isoformat(),'providers':providers,
         'intl':intl,'dom':dom,'trans':trans,
         'src':{'api':'FAO GIEWS FPMA Tool v4 public API (fpma.fao.org/giews/v4/global)',
                'n_intl':len(intl),'n_dom':len(dom),'n_ctry':len({d['c'] for d in dom})}}
json.dump(payload,open('data/payload.json','w'),separators=(',',':'))
import os; print("payload:",os.path.getsize('data/payload.json'),"bytes")
