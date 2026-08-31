"""Build the trade-map payload: world topology + bilateral flows + FPMA price status."""
import json, collections, math, os

SC = '/private/tmp/claude-501/-Users-ybl-Desktop-Resume/41eda02a-5815-40f0-a57b-edac92b1da62/scratchpad'
DB = '/Users/ybl/Desktop/Resume/FAO YPP EST Economist/dashboard'

# ---------- ISO reference ----------
iso = json.load(open(f'{SC}/iso.json'))
NUM2A3, A32NUM, NUM2NAME, NUM2REG = {}, {}, {}, {}
for c in iso:
    n = str(int(c['country-code']))
    NUM2A3[n] = c['alpha-3']; A32NUM[c['alpha-3']] = n
    NUM2NAME[n] = c['name']; NUM2REG[n] = c['sub-region'] or c['region']

# ---------- world topology: decode arcs only to get centroids ----------
W = json.load(open(f'{SC}/world.json'))
tr = W['transform']; sx, sy = tr['scale']; tx, ty = tr['translate']
def arc_pts(a):
    x = y = 0; out = []
    for dx, dy in a:
        x += dx; y += dy
        out.append((x*sx+tx, y*sy+ty))
    return out
ARCS = [arc_pts(a) for a in W['arcs']]
def ring(idxs):
    pts = []
    for i in idxs:
        a = ARCS[~i][::-1] if i < 0 else ARCS[i]
        pts.extend(a if not pts else a[1:])
    return unwrap(pts)

def unwrap(pts):
    """Make longitudes continuous across the antimeridian so area and centroid
    are computed on the real polygon rather than one torn in half."""
    if not pts: return pts
    out=[pts[0]]
    for lo,la in pts[1:]:
        plo=out[-1][0]
        while lo-plo > 180: lo -= 360
        while lo-plo < -180: lo += 360
        out.append((lo,la))
    return out
def ring_area_centroid(r):
    A = cx = cy = 0.0
    for i in range(len(r)-1):
        x0, y0 = r[i]; x1, y1 = r[i+1]
        f = x0*y1 - x1*y0
        A += f; cx += (x0+x1)*f; cy += (y0+y1)*f
    if abs(A) < 1e-12:
        xs = [p[0] for p in r]; ys = [p[1] for p in r]
        return 0.0, (sum(xs)/len(xs), sum(ys)/len(ys))
    A *= 0.5
    return abs(A), (cx/(6*A), cy/(6*A))

CENT = {}
for g in W['objects']['countries']['geometries']:
    cid = str(int(g['id'])) if str(g.get('id','')).strip().isdigit() else None
    if not cid: continue
    polys = g['arcs'] if g['type'] == 'MultiPolygon' else [g['arcs']]
    best = (0, None)
    for poly in polys:
        a, c = ring_area_centroid(ring(poly[0]))
        if a > best[0]: best = (a, c)
    if best[1]:
        lo = best[1][0]
        while lo > 180: lo -= 360
        while lo < -180: lo += 360
        CENT[cid] = [round(lo, 2), round(best[1][1], 2)]
print(f'centroids: {len(CENT)}')

# ---------- trade edges: reported, backfilled with mirror ----------
E = json.load(open(f'{SC}/trade_edges.json'))
YEAR = max(x['y'] for x in E)
GROUPS = ['Wheat', 'Maize', 'Rice', 'Soybeans', 'Sugar', 'Palm oil', 'Barley', 'Sorghum']
rep, mir = collections.defaultdict(float), collections.defaultdict(float)
for x in E:
    if x['y'] != YEAR or x['g'] not in GROUPS: continue
    (rep if x['s'] == 'rep' else mir)[(x['g'], x['e'], x['i'])] += x['v']
# a reporter that filed nothing at all this year is backfilled from mirror
filed = {(g, e) for (g, e, i) in rep}
edges = dict(rep)
n_mir = 0
for k, v in mir.items():
    g, e, i = k
    if (g, e) not in filed:
        edges[k] = v; n_mir += 1
print(f'year {YEAR}: {len(rep):,} reported edges, {n_mir:,} backfilled from mirror')

TOPN = 8
ctry = collections.defaultdict(lambda: collections.defaultdict(lambda: {'x': 0.0, 'm': 0.0, 'xd': [], 'mo': []}))
ex_by = collections.defaultdict(lambda: collections.defaultdict(float))
im_by = collections.defaultdict(lambda: collections.defaultdict(float))
for (g, e, i), v in edges.items():
    ex_by[(g, e)][i] += v
    im_by[(g, i)][e] += v
allc = {c for (_, c) in list(ex_by) + list(im_by)}
for g in GROUPS:
    for c in allc:
        d = ctry[c][g]
        xs = ex_by.get((g, c), {}); ms = im_by.get((g, c), {})
        d['x'] = round(sum(xs.values()))
        d['m'] = round(sum(ms.values()))
        d['xd'] = [[p, round(v)] for p, v in sorted(xs.items(), key=lambda a: -a[1])[:TOPN] if p in CENT]
        d['mo'] = [[p, round(v)] for p, v in sorted(ms.items(), key=lambda a: -a[1])[:TOPN] if p in CENT]
        if not d['x'] and not d['m']: del ctry[c][g]

# ---------- FPMA domestic price status, joined by ISO3 -> M49 ----------
P = json.load(open(f'{DB}/data/payload.json'))
price = collections.defaultdict(dict)
unmatched = set()
for d in P['dom']:
    num = A32NUM.get((d.get('iso') or '').upper())
    if not num:
        unmatched.add(d['c']); continue
    price[num][d['st']] = {'ipa': d['ipa'], 'flag': d['flag'], 'yoyR': d['yoyR'],
                           'yoyN': d['yoyN'], 'n': d['n'], 'cur': d['cur'], 'u': d['u'], 'last': d['last']}
print(f'price countries matched: {len(price)}; unmatched: {sorted(unmatched)[:8]}')

names = {c: NUM2NAME.get(c, c) for c in set(list(ctry) + list(price) + list(CENT))}
out = {
    'year': YEAR, 'groups': GROUPS, 'topo': W, 'cent': CENT,
    'names': names, 'reg': {c: NUM2REG.get(c, '') for c in names},
    'trade': {c: dict(v) for c, v in ctry.items() if v},
    'price': dict(price),
    'mirrorBackfilled': n_mir,
}
p = f'{DB}/data/map_payload.json'
json.dump(out, open(p, 'w'), separators=(',', ':'))
print('map payload', os.path.getsize(p), 'bytes;', len(out['trade']), 'trading countries')
