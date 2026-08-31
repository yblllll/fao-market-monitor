# Agricultural Market Monitor

An independent rebuild of FAO's **Food Price Monitoring and Analysis (FPMA)** tool, built from
the live GIEWS API and the FAOSTAT detailed trade matrix.

**Live: https://yblllll.github.io/fao-market-monitor/**

Not an FAO publication. FAO publishes the official version of these indicators through the
[FPMA Tool](https://fpma.fao.org/giews/fpmat4/); everything here is computed independently.

---

## What it shows

| Layer | Content |
|---|---|
| 1 · International quotations | All 90 international price series FAO tracks, with 1m / 12m / 36m changes and an anomaly score |
| 2 · Origin spreads | The same grain priced across every origin FAO monitors (wheat has 11, rice 13) |
| 3 · Domestic prices | 230 national-average retail series across 76 countries, CPI-deflated, screened with SDG 2.c.1 |
| 4 · Trade network | Bilateral trade in eight staples on a draggable, zoomable world map |
| 5 · Price drivers | Brent crude and Black Sea urea pass-through to grain export quotations |

## Data sources

* **FAO GIEWS FPMA v4 API** — `fpma.fao.org/giews/v4/global/price_module/api/v1/`.
  Public REST. Requires a browser `User-Agent`; the default `Python-urllib` string returns 403.
  Endpoints used: `FpmaSerieInternational/`, `FpmaSerie/`, `FpmaSeriePrice/?uuid__in=`, `Market/`.
* **FAOSTAT Detailed Trade Matrix** — 52.4 M rows, 8.1 GB uncompressed, streamed and filtered
  without extraction.
* **world-atlas 110m TopoJSON** — country ids are ISO numeric, which is M49, so it joins to
  FAOSTAT directly.

Underlying price sources named by FAO per series include the International Grains Council, USDA,
Oil World, the FAO rice price update, APK-Inform, the International Sugar Organization, Dairy
Market News and the World Bank Pink Sheet.

## Two things worth knowing

**The anomaly indicator matches FAO's own implementation.** The published SDG 2.c.1 metadata gives
the formula but not the weights. FAO computes the indicator client-side, so the real scheme is in
the FPMA JavaScript bundle: a linear ramp over strictly-prior years, an (n−1)/n bias correction on
the weighted standard deviation, and the annual arm run on the series with its first year dropped.
`ipa_fao.py` implements exactly that. Using equal weights instead flags 8 countries as abnormally
high; FAO's scheme flags 18.

**The Russian Federation has filed no FAOSTAT trade return since 2021.** Taken at face value the
world's largest wheat exporter reads as zero from 2022. Flows for any country that filed nothing
in the year are reconstructed from partner-reported imports (3,480 mirrored edges), which restores
Russia to 30.1 Mt for 2024 with Egypt, Türkiye and Saudi Arabia as its largest destinations.

See [VALIDATION.md](VALIDATION.md) for the cross-check against the World Bank Pink Sheet
(11 series reproduce the primary source exactly over 312 months) and for what was *not* verified.

## Rebuilding

```bash
python3 fetch_all.py       # FPMA price series           -> data/intl_prices.json, data/domestic_prices.json
python3 extract_trade.py   # FAOSTAT trade matrix         -> data/trade_edges.json   (needs tm.zip, 420 MB)
python3 analyse.py         # SDG 2.c.1 + pass-through     -> data/payload.json
python3 build_map.py       # topology + flows + join      -> data/map_payload.json
python3 - <<'PY'
t=open('template.html').read()
t=t.replace('/*__PAYLOAD__*/null', open('data/payload.json').read())
t=t.replace('/*__MAP__*/null', open('data/map_payload.json').read())
open('index.html','w').write(t)
PY
```

`tm.zip` is not committed. Fetch it from
`https://bulks-faostat.fao.org/production/Trade_DetailedTradeMatrix_E_All_Data_(Normalized).zip`.

## Method

**SDG 2.c.1.** `CGR = (P_t / P_{t−k})^(1/k) − 1` for k = 3 and 12, each standardised against the
same calendar month across prior years, combined as `IFPA = 0.4·Quarterly + 0.6·Annual`. Below 0.5
normal, 0.5–1.0 moderately high, 1.0 and above abnormally high. Domestic series are screened on
CPI-deflated prices, international series on nominal US dollars.

**Pass-through.** `Δln(grain) = α + Σβⱼ Δln(Brent)ₜ₋ⱼ + Σγⱼ Δln(urea)ₜ₋ⱼ + ε`, j = 0…6, OLS with
Newey–West HAC at six lags. The cumulative elasticity's standard error is `sqrt(R'VR)` from the
full HAC covariance, so covariance between lag coefficients is carried rather than dropped. Over
the full sample nothing is significant; from 2019 cumulative fertiliser pass-through is 0.42
(t = 3.26) to US HRW wheat and 0.31 (t = 2.59) to US maize, and nothing to Thai rice. It is a
reduced-form association, not a causal estimate.

## Licence and attribution

FAO. 2026. *Global Information and Early Warning System on Food and Agriculture (GIEWS): Food Price
Monitoring and Analysis Tool.* Accessed on 31 August 2026. https://fpma.fao.org/giews/fpmat4/
Licence: CC BY 4.0.

FAO statistical databases are released under CC BY 4.0. This rebuild adapts that data and is
redistributed on the same terms. FAO has not reviewed or endorsed it.

Built by Yibin Li.
