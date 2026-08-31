"""One place that decides how a country is named, so the price tables, the map and
the trade rankings never disagree. Resolution order: ISO 3166 short name looked up
by alpha-3 or M49, then a common-usage override for the inverted or ceremonial forms."""
import json, os
_HERE = os.path.dirname(os.path.abspath(__file__))
_iso = json.load(open(os.path.join(_HERE, 'data', 'iso.json')))
A3 = {c['alpha-3']: c['name'] for c in _iso}
NUM = {str(int(c['country-code'])): c['name'] for c in _iso}
A3_TO_NUM = {c['alpha-3']: str(int(c['country-code'])) for c in _iso}

SHORT = {
 'Bolivia, Plurinational State of': 'Bolivia',
 'Venezuela, Bolivarian State of': 'Venezuela',
 'Venezuela, Bolivarian Republic of': 'Venezuela',
 'Iran, Islamic Republic of': 'Iran',
 'Korea, Republic of': 'South Korea',
 "Korea, Democratic People's Republic of": 'North Korea',
 "Lao People's Democratic Republic": 'Laos',
 'Moldova, Republic of': 'Moldova',
 'Tanzania, United Republic of': 'Tanzania',
 'Russian Federation': 'Russia',
 'Syrian Arab Republic': 'Syria',
 'Congo, Democratic Republic of the': 'DR Congo',
 'United Kingdom of Great Britain and Northern Ireland': 'United Kingdom',
 'United States of America': 'United States',
 'Micronesia, Federated States of': 'Micronesia',
 'Palestine, State of': 'Palestine',
 'Netherlands, Kingdom of the': 'Netherlands',
 'Bolivia (Plurinational State of)': 'Bolivia',
 'Czechia': 'Czechia',
 'Türkiye': 'Türkiye',
 'Viet Nam': 'Viet Nam',
 'Central African Republic': 'Central African Rep.',
 'United Arab Emirates': 'UAE',
 'Dominican Republic': 'Dominican Rep.',
 'Bosnia and Herzegovina': 'Bosnia & Herz.',
 'North Macedonia': 'North Macedonia',
 'Saint Vincent and the Grenadines': 'St Vincent & Gren.',
 'Trinidad and Tobago': 'Trinidad & Tobago',
 'Antigua and Barbuda': 'Antigua & Barbuda',
 'Saint Kitts and Nevis': 'St Kitts & Nevis',
 'Sao Tome and Principe': 'Sao Tome & Principe',
 'Papua New Guinea': 'Papua New Guinea',
 'Lao People’s Democratic Republic': 'Laos',
}

def by_a3(a3, fallback=None):
    n = A3.get((a3 or '').upper())
    return SHORT.get(n, n) if n else (fallback or a3)

def by_num(num, fallback=None):
    n = NUM.get(str(num))
    return SHORT.get(n, n) if n else (fallback or str(num))
