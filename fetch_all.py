import json, urllib.request, time, os
B="https://fpma.fao.org/giews/v4/global/price_module/api/v1"
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
def get(u):
    for a in range(5):
        try:
            req=urllib.request.Request(u); req.add_header('User-Agent',UA)
            with urllib.request.urlopen(req,timeout=120) as r: return json.load(r)
        except Exception as e:
            print("   retry",a,repr(e)[:70],flush=True); time.sleep(3*(a+1))
    return None

def pull(sel,label,path,metafn):
    out={}
    CH=8
    for i in range(0,len(sel),CH):
        ch=sel[i:i+CH]
        d=get(B+"/FpmaSeriePrice/?uuid__in="+",".join(x['uuid'] for x in ch))
        if not d: print(" FAIL",i,flush=True); continue
        for r in d.get('results',[]): out[r['uuid']]=r.get('datapoints',[])
        print(f" {label} {min(i+CH,len(sel))}/{len(sel)} pts={sum(len(v) for v in out.values())}",flush=True)
    json.dump({'meta':[metafn(x) for x in sel],'data':out},open(path,'w'))
    print(f"SAVED {path} {os.path.getsize(path)}B series={len(out)}",flush=True)

# ---------- international ----------
intl=json.load(open('data/price_module_api_v1_FpmaSerieInternational_.json'))['results']
KEEP=('uuid','country_name','market_name','market_type','commodity_name','commodity_code',
      'price_type','currency','measure_unit_label','source_name','periodicity')
pull(intl,"INTL","data/intl_prices.json", lambda x:{k:x.get(k) for k in KEEP})

# ---------- domestic (national average, monthly, active) ----------
allS=json.load(open('data/price_module_api_v1_FpmaSerie_.json'))['results']
STAPLES=[('Wheat',('wheat',)),('Maize',('maize',)),('Rice',('rice',)),('Vegetable oil',('oil',)),
         ('Beans',('bean',)),('Sugar',('sugar',)),('Potatoes',('potato',)),('Sorghum',('sorghum',)),
         ('Millet',('millet',)),('Cassava',('cassava',))]
def staple(n):
    n=n.lower()
    for lab,ks in STAPLES:
        if any(k in n for k in ks): return lab
def mper(x):
    p=[q for q in (x.get('periodicity') or []) if q.get('period')=='monthly']
    return p[0] if p else None
best={}
for x in allS:
    p=mper(x)
    if not p or (p.get('end_date') or '')<'2025-07-01': continue
    if 'national' not in (x['market_name'] or '').lower(): continue
    s=staple(x['commodity_name'])
    if not s: continue
    k=(x['country_name'],s); st=p.get('start_date') or '9999'
    if k not in best or st<best[k][1]: best[k]=(x,st,s)
sel=[v[0] for v in best.values()]; smap={v[0]['uuid']:v[2] for v in best.values()}
print(f"domestic selected {len(sel)} series / {len({x['country_name'] for x in sel})} countries",flush=True)
pull(sel,"DOM","data/domestic_prices.json",
     lambda x:{**{k:x.get(k) for k in KEEP},'iso3':x.get('iso3_country_code'),'staple':smap[x['uuid']]})
print("ALL DONE",flush=True)
