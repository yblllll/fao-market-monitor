import zipfile, io, csv, json, collections, time
Z='tm.zip'; N='Trade_DetailedTradeMatrix_E_All_Data_(Normalized).csv'
KEEP={'wheat':'Wheat','maize':'Maize','rice':'Rice','barley':'Barley','sorghum':'Sorghum',
      'soya bean':'Soybeans','soybean':'Soybeans','palm oil':'Palm oil','sugar':'Sugar',
      'cassava':'Cassava','millet':'Millet','potato':'Potatoes'}
def grp(s):
    s=s.lower()
    for k,v in KEEP.items():
        if k in s: return v
def m49(c): return c.strip().strip("'").lstrip('0') or '0'
out=collections.defaultdict(float)
t0=time.time(); n=0; kept=0
z=zipfile.ZipFile(Z)
with z.open(N) as f:
    tr=io.TextIOWrapper(f,encoding='utf-8',errors='replace'); r=csv.reader(tr); next(r)
    for row in r:
        n+=1
        if n%25_000_000==0: print(f"  {n/1e6:.0f}M rows {time.time()-t0:.0f}s",flush=True)
        if len(row)<15: continue
        el=row[10]
        if el not in ('Export quantity','Import quantity'): continue
        y=row[12]
        if y<'2022': continue
        g=grp(row[8])
        if not g: continue
        try: v=float(row[14])
        except: continue
        if v<=0: continue
        # normalise every row into an EXPORTER -> IMPORTER edge
        if el=='Export quantity':  ex,im,src = m49(row[1]), m49(row[4]), 'rep'
        else:                      ex,im,src = m49(row[4]), m49(row[1]), 'mir'
        out[(g,int(y),ex,im,src)] += v
        kept+=1
print(f"done {n:,} rows {time.time()-t0:.0f}s kept {kept:,}",flush=True)
recs=[{'g':k[0],'y':k[1],'e':k[2],'i':k[3],'s':k[4],'v':round(v,1)} for k,v in out.items()]
json.dump(recs,open('trade_edges.json','w'),separators=(',',':'))
names={}
with z.open('Trade_DetailedTradeMatrix_E_ReporterCountries.csv') as f:
    for row in csv.reader(io.TextIOWrapper(f,encoding='utf-8-sig',errors='replace')):
        if row and row[0]!='Reporter Country Code': names[m49(row[1])]=row[2]
with z.open('Trade_DetailedTradeMatrix_E_PartnerCountries.csv') as f:
    for row in csv.reader(io.TextIOWrapper(f,encoding='utf-8-sig',errors='replace')):
        if row and row[0]!='Partner Country Code': names.setdefault(m49(row[1]),row[2])
json.dump(names,open('m49_names.json','w'))
import os; print("edges",len(recs),os.path.getsize('trade_edges.json'),"| names",len(names),flush=True)
