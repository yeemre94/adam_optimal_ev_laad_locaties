# Optimal Locations for EV Charging Stations in Amsterdam

A spatial analysis that identifies high-population-density areas in
Amsterdam that fall **outside the coverage area (250 m)** of existing
charging stations, and based on that proposes the **10 best new locations
for EV charging stations** — based on **real open data**.

**Result:** [`outputs/top10_kandidaten.csv`](outputs/top10_kandidaten.csv)


## Data sources used (real)

| Source | Content | File |
|---|---|---|
| City of Amsterdam | Neighborhood boundaries with CBS neighborhood codes (517 neighborhoods) | `data/ruw/buurten_amsterdam_lat_lon.json` |
| CBS — "Kerncijfers wijken en buurten" (table 86165NED) | Number of inhabitants per neighborhood | `data/ruw/cbs_kerncijfers_wijken_buurten.csv` |
| Open Charge Map (OCM) | 673 existing charging locations in Amsterdam | `data/ruw/laadpalen_ocm.json` |

`src/verwerk_echte_data.py` converts these three raw files into the usable
GeoJSON files in `data/echt/` (same schema the analysis code expects).
Note: the City of Amsterdam's neighborhood GeoJSON uses coordinates in
`[lat, lon]` order instead of the GeoJSON standard `[lon, lat]` — this
script corrects that automatically.

Of the 518 neighborhoods in the source data, 1 could not be matched to a
CBS population figure (no match on neighborhood code) and was skipped.

## Tools used

- **Python**: GeoPandas, Pandas, Shapely, Folium
- **Jupyter Notebook**: step-by-step analysis and visualization

## Project structure

```
ev-project/
├── data/
│   ├── ruw/
│   │   ├── buurten_amsterdam_lat_lon.json      # Neighborhood boundaries (City of Amsterdam)
│   │   ├── cbs_kerncijfers_wijken_buurten.csv  # CBS population figures
│   │   └── laadpalen_ocm.json                  # Open Charge Map export
│   └── echt/
│       ├── buurten_amsterdam.geojson           # Processed: neighborhoods + population density
│       └── ev_laadpalen_bestaand.geojson       # Processed: existing charging stations
├── notebooks/
│   └── ev_laadpaal_analyse.ipynb               # Main analysis (with executed output)

├── outputs/
│   ├── top10_kandidaten.csv                    # Result: top 10 proposed locations
│   └── interactieve_kaart                      # Interactive Folium map #in progress#
├── src/
│   ├── verwerk_echte_data.py                   # Converts raw source data into usable GeoJSON
│   ├── analyse.py                              # Buffer / coverage-gap / scoring functions
│   └── bouw_kaart.py                           # Builds the Folium map
├── requirements.txt
└── README.md
```

## Installation and usage

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Convert raw source data into usable GeoJSON (already prepared in data/echt/):
python3 src/verwerk_echte_data.py

# Run the analysis and build the interactive map:
cd src && python3 bouw_kaart.py

# Or step through it via the notebook:
jupyter notebook notebooks/ev_laadpaal_analyse.ipynb
```

## Method

1. **Load data** — neighborhood boundaries (polygons) with population
   density, existing charging stations (points) from Open Charge Map.
2. **250 m buffer** — a 250-meter coverage area is calculated around each
   existing charging station (metric CRS: EPSG:28992, Amersfoort/RD New).
3. **Areas outside coverage** — the buffer area is subtracted from the
   neighborhood polygons (`geopandas.GeoSeries.difference`); what remains
   is the area without coverage.
4. **Priority neighborhoods** — neighborhoods with a population density
   above the median **and** where at least 35% of the area falls outside
   the coverage zone.
5. **Generate and score candidate points** — random candidate points are
   generated within the uncovered portion of each priority neighborhood.
   Each point gets a score from 0-100 based on
   `0.45×density + 0.35×distance_to_nearest_station + 0.20×uncovered_share`;
   candidates within 300 m of an already-chosen location are excluded.
6. **Top 10** — the 10 highest-scoring candidates are written to
   `outputs/top10_kandidaten.csv` and shown on the interactive map.

## Refreshing the data

Want to work with a newer version of the source data (e.g. a more recent
OCM export)? Replace the relevant file in `data/ruw/` and run again:

```bash
python3 src/verwerk_echte_data.py
cd src && python3 bouw_kaart.py
```


## License

CBS data: CC-BY 4.0. Open Charge Map data: open data, community-maintained
(see [openchargemap.org](https://openchargemap.org) for license details
per data source). City of Amsterdam neighborhood data: see the terms at
[data.amsterdam.nl](https://data.amsterdam.nl).
