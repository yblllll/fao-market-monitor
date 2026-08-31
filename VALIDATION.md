# What was verified, and what was not

## Verified — price series against the primary source

FPMA re-disseminates several international quotations from the World Bank Pink Sheet.
Downloading the Pink Sheet independently and comparing month by month over 2000–2025
(312 monthly observations each):

| FPMA series | Pink Sheet column | n | corr | median deviation |
|---|---|---:|---:|---:|
| Crude oil (Brent) | Crude oil, Brent | 312 | 0.9998 | 0.00% |
| Crude oil (WTI) | Crude oil, WTI | 312 | 1.0000 | 0.00% |
| Urea (N fertilizer) | Urea | 312 | 1.0000 | 0.00% |
| Diammonium phosphate, DAP | DAP | 312 | 1.0000 | 0.00% |
| Potassium chloride (potash) | Potassium chloride | 312 | 1.0000 | 0.00% |
| Phosphate rock | Phosphate rock | 311 | 1.0000 | 0.00% |
| Triple Superphosphate, TSP | TSP | 312 | 1.0000 | 0.00% |
| Sugar | Sugar, world | 277 | 1.0000 | 0.01% |
| Coconut oil | Coconut oil | 312 | 0.9990 | 0.02% |
| Soybean oil | Soybean oil | 312 | 0.9979 | 0.50% |
| Soybeans | Soybeans | 312 | 0.9916 | 0.43% |

Eleven series reproduce the primary source exactly. That validates the whole extraction
path: API call, unit handling, date alignment, and storage.

Remaining comparisons differ because they are **different quotations**, not because of an
extraction error: palm oil (3.2%) and groundnut oil (6.2%) are quoted on a different
delivery basis; soybean meal is 44/45% Hamburg f.o.b. against a different Pink Sheet spec;
the tea comparison is Mombasa auction against a three-auction average (corr 0.54); and two
of the mappings were simply wrong products on my side (FPMA rapeseed *seed* against Pink
Sheet rapeseed *oil*, ratio 0.47; bananas per 18.14 kg box against per tonne).

## Verified — the anomaly indicator matches FAO's own implementation

The published SDG 2.c.1 metadata gives the formula but says only that the historical mean
and standard deviation are "weighted", without publishing the weights. The first version of
this rebuild used equal weights and said so.

FAO's FPMA front end computes the indicator client-side, so the real implementation is in
its JavaScript bundle. Reading it (`main.*.js`, the IPA calculator) recovered the scheme:

* weights over prior years are a **linear ramp**, raw weights 1, 2, …, k for the k years
  before the current one, normalised to sum to 1, so the most recent prior year carries the
  most weight and **the current year is excluded**;
* the weighted standard deviation carries an **(n−1)/n bias correction**, n = years elapsed;
* the annual arm runs on the series with its first year dropped;
* `IFPA = 0.4·Quarterly + 0.6·Annual`, defined only from month 36.

`ipa_fao.py` implements exactly that. It is a faithful transcription of FAO's code, not a
guess. Switching from equal weights to FAO's scheme changed the count of countries flagged
"abnormally high" from 8 to 18, so the weighting is not a detail.

**Not done:** the values have not been compared numerically against what the FPMA web tool
renders on screen. The API exposes prices, not the computed indicator, and driving the
Angular UI to read it back was not attempted.

## Verified — trade totals against known market structure

2024 top wheat exporters after mirror reconstruction: Russian Federation 30.1 Mt, Canada
25.8, United States 22.4, Ukraine 21.1, Australia 19.8, France 15.7. Top maize exporters:
United States 63.4 Mt, Brazil 40.7, Argentina 32.0, Ukraine 29.7. Both match the known
ordering and magnitude of world trade.

**A real gap, handled:** the Russian Federation has filed no return to the FAOSTAT detailed
trade matrix since 2021 (33.0 Mt wheat in 2019, 38.4 in 2020, 28.6 in 2021, then zero).
Taken at face value the world's largest wheat exporter disappears. Flows for any country
that filed nothing in the year are therefore reconstructed from partner-reported imports —
3,480 mirrored edges — which restores Russia to 30.1 Mt with Egypt (9.0), Türkiye (6.1) and
Saudi Arabia (2.1) as its largest destinations.

## Not verified

* Domestic retail price levels against national statistical offices. FPMA is the only source
  used and there is no independent series to check them against.
* Whether FPMA's own re-dissemination of third-party quotations (IGC, USDA, Oil World,
  APK-Inform, the Thai Rice Exporters Association) matches those originals. Only the World
  Bank-sourced subset could be checked, because only that source is openly downloadable.
* The pass-through regression is a reduced-form association on 83 monthly observations in
  the 2019+ window. It is not identified as causal and is not presented as such.

## Country naming

All country labels resolve through one table (`names.py`): FPMA's ISO alpha-3 and FAOSTAT's M49
are both looked up against ISO 3166, then a common-usage override shortens the inverted and
ceremonial forms. This replaced FPMA's raw strings, which were long and inconsistently cased
("Libyan Arab Jamahiriya", "Lao People'S Democratic Republic", "Republic Of Moldova"). The map,
the price tables and the trade rankings now draw from the same table, so they cannot disagree.

## A second data-quality problem, found and flagged

Recomputing the 12-month changes directly from the raw FPMA datapoints reproduces the dashboard
exactly for every series checked. But one of those checks surfaced a problem in the source data.

Tajikistan's wheat flour reads **−4.0% nominal and +30.2% real** over the year to June 2026. The
implied deflator (nominal ÷ real) therefore fell 26%, which is not deflation — it is a rebasing of
the national CPI. Scanning every series for single-month deflator moves above 15% finds breaks in
11 countries, of which four fall inside the current comparison window: **Djibouti, Iraq, Nigeria
and Tajikistan**. Tajikistan's deflator jumps 242% in January 2025.

These series are marked rather than dropped: a dashed outline on the bar, an exclamation mark in
the table, an explanation in the tooltip, and an entry in the chart legend. Their real change and
their SDG 2.c.1 score should not be read as measurements.

## Trade rankings sanity check

Top rice exporters 2024 as computed: India, Thailand, Viet Nam, Pakistan, Cambodia, United States.
Top rice importers: Viet Nam, Philippines, Indonesia, Benin, Côte d'Ivoire, Iraq. Top wheat
importers: Egypt, Indonesia, China, Spain, Italy, Türkiye, Brazil, Algeria. All match the known
structure of those markets.
