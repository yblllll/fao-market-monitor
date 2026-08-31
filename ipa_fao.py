"""SDG 2.c.1 Indicator of Food Price Anomalies, reimplemented to match FAO's
own FPMA Tool v4 client implementation (main.*.js, IpaCalculator).

Differences from the published metadata template, recovered from FAO's code:
  * the historical mean/SD across years is weighted with a LINEAR RAMP over
    strictly-prior years: for the year at index k, prior years 0..k-1 receive
    raw weights 1,2,...,k normalised to sum 1, so the most recent prior year
    carries the most weight and the current year is excluded;
  * the weighted SD carries a (n-1)/n bias correction, n = years elapsed;
  * quarterly weight uses column k = year index, annual uses column k-1 on a
    series whose first year has been dropped;
  * IFPA = 0.4*Quarterly + 0.6*Annual, defined only from month index 36.
"""
import math

def _cgr(p, k):
    n=len(p); out=[None]*n
    for t in range(k,n):
        a,b=p[t-k],p[t]
        if a and b and a>0 and b>0: out[t]=(b/a)**(1.0/k)-1.0
    return out

def _by_month(seq):
    """lodash unzip(chunk(seq,12)) -> 12 lists, ragged padded with None"""
    rows=[seq[i:i+12] for i in range(0,len(seq),12)]
    m=max((len(r) for r in rows), default=0)
    return [[ (r[j] if j<len(r) else None) for r in rows ] for j in range(m)]

def _weights(r):
    """FAO's column-normalised linear ramp. Returns cols[T] = weight vector."""
    if r<=0: return []
    I=[[0]*(r-1) for _ in range(r)]
    for fe in range(r):
        for l1 in range(r-1):
            I[fe][l1] = 0 if l1<fe else fe+1
    for fe in range(r):
        I[fe].insert(0, 1 if fe==0 else 0)
    de=[[0.0]*r for _ in range(r)]
    for T in range(r):
        cs=sum(I[j][T] for j in range(r))
        for j in range(r):
            de[j][T] = 0.0 if ((j==0 and T==0) or I[j][T]==0 or cs==0) else I[j][T]/cs
    return [[de[j][T] for j in range(r)] for T in range(r)]   # cols[T]

def _sumprod(vals, w):
    if w is None: return 0.0
    s=0.0
    for i in range(min(len(vals),len(w))):
        v=vals[i]
        s += (0.0 if v is None else v)*w[i]
    return s

def _wsd(vals, w, mean, n_years):
    if w is None or n_years is None or n_years<=1: return None
    num=0.0
    for i in range(min(len(vals),len(w))):
        v=vals[i]
        if v is None: continue
        num += (v-mean)**2 * w[i]
    den = sum(w)*(n_years-1)/n_years
    if den<=0: return None
    return math.sqrt(num/den)

def ipa_series(prices, first_year):
    """prices: dense monthly list starting at JANUARY of first_year (None for gaps).
    Returns list of IFPA values, same length, None where undefined."""
    T=len(prices); r=math.ceil(T/12)
    q,a=_cgr(prices,3),_cgr(prices,12)
    Lt=_by_month(q)                       # quarterly, chunked from month 0
    Jt=_by_month(a[12:])                  # annual, first year dropped (FAO: slice(yt,12,..))
    Yi=_weights(r); Nu=_weights(r-1)
    QA=[None]*T; QS=[None]*T; AA=[None]*T; AS=[None]*T
    for fe in range(T):
        yr, mo = fe//12, fe%12
        Ro = yr-1
        if fe>=15 and 0<=Ro+1<len(Yi) and mo<len(Lt):
            QA[fe]=_sumprod(Lt[mo], Yi[Ro+1])
        if fe>=24 and 0<=Ro<len(Nu) and mo<len(Jt):
            AA[fe]=_sumprod(Jt[mo], Nu[Ro])
    for fe in range(T):
        yr, mo = fe//12, fe%12
        Ro = yr-1
        if fe>=24 and QA[fe] is not None and 0<=Ro+1<len(Yi) and mo<len(Lt):
            QS[fe]=_wsd(Lt[mo], Yi[Ro+1], QA[fe], yr)          # $0 = year - first_year
        if fe>=36 and AA[fe] is not None and 0<=Ro<len(Nu) and mo<len(Jt):
            AS[fe]=_wsd(Jt[mo], Nu[Ro], AA[fe], yr-1)          # $0 = year - first_year - 1
    out=[None]*T
    for fe in range(36,T):
        if q[fe] is None or a[fe] is None: continue
        if not QS[fe] or not AS[fe]: continue
        Q=(q[fe]-QA[fe])/QS[fe]; A=(a[fe]-AA[fe])/AS[fe]
        v=0.4*Q+0.6*A
        if math.isfinite(v): out[fe]=v
    return out
