# Optimale Locaties voor EV-Laadpalen in Amsterdam

Een ruimtelijke analyse die voor Amsterdam de gebieden met een hoge
bevolkingsdichtheid identificeert die **buiten het dekkingsgebied (250 m)**
van bestaande laadpalen vallen, en op basis daarvan de **10 beste nieuwe
locaties voor EV-laadpalen** voorstelt — gebaseerd op **echte open data**.

**Resultaat:** [`outputs/top10_kandidaten.csv`](outputs/top10_kandidaten.csv)


## Gebruikte databronnen (echt)

| Bron | Inhoud | Bestand |
|---|---|---|
| Gemeente Amsterdam | Buurtgrenzen met CBS-buurtcodes (517 buurten) | `data/ruw/buurten_amsterdam_lat_lon.json` |
| CBS — "Kerncijfers wijken en buurten" (tabel 86165NED) | Aantal inwoners per buurt | `data/ruw/cbs_kerncijfers_wijken_buurten.csv` |
| Open Charge Map (OCM) | 673 bestaande laadlocaties in Amsterdam | `data/ruw/laadpalen_ocm.json` |

`src/verwerk_echte_data.py` zet deze drie ruwe bestanden om naar de
bruikbare GeoJSON-bestanden in `data/echt/` (zelfde schema als de
analysecode verwacht). Let op: de buurten-GeoJSON van de gemeente
Amsterdam gebruikt coördinaten in de volgorde `[lat, lon]` in plaats van
de GeoJSON-standaard `[lon, lat]` — dit script corrigeert dat automatisch.

Van de 518 buurten in de brondata kon 1 buurt niet aan een CBS-bevolkingscijfer
gekoppeld worden (geen match op buurtcode) en is overgeslagen.

## Gebruikte tools

- **Python**: GeoPandas, Pandas, Shapely, Folium
- **Jupyter Notebook**: stapsgewijze analyse en visualisatie
- **QGIS**: visuele laagcontrole en verificatie (zie `qgis/QGIS_HANDLEIDING.md`)

## Projectstructuur

```
ev-project/
├── data/
│   ├── ruw/
│   │   ├── buurten_amsterdam_lat_lon.json      # Buurtgrenzen (gemeente Amsterdam)
│   │   ├── cbs_kerncijfers_wijken_buurten.csv  # CBS-bevolkingscijfers
│   │   └── laadpalen_ocm.json                  # Open Charge Map-export
│   └── echt/
│       ├── buurten_amsterdam.geojson           # Verwerkt: buurten + bevolkingsdichtheid
│       └── ev_laadpalen_bestaand.geojson       # Verwerkt: bestaande laadpalen
├── notebooks/
│   └── ev_laadpaal_analyse.ipynb               # Hoofdanalyse (met uitgevoerde output)

├── outputs/
│   ├── top10_kandidaten.csv                    # Resultaat: top 10 voorgestelde locaties
│   └── interactieve_kaart                      # Interactieve Folium-kaart #in progres#
├── src/
│   ├── verwerk_echte_data.py                   # Zet ruwe brondata om naar bruikbare GeoJSON
│   ├── analyse.py                              # Buffer / dekkingsgat / scoring-functies
│   └── bouw_kaart.py                           # Bouwt de Folium-kaart
├── requirements.txt
└── README.md
```

## Installatie en gebruik

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Ruwe brondata omzetten naar bruikbare GeoJSON (staat al klaar in data/echt/):
python3 src/verwerk_echte_data.py

# Analyse uitvoeren en de interactieve kaart bouwen:
cd src && python3 bouw_kaart.py

# Of stap voor stap doorlopen via de notebook:
jupyter notebook notebooks/ev_laadpaal_analyse.ipynb
```

## Methode

1. **Data inladen** — buurtgrenzen (polygonen) met bevolkingsdichtheid,
   bestaande laadpalen (punten) uit Open Charge Map.
2. **Buffer van 250 m** — rondom elke bestaande laadpaal wordt een
   dekkingsgebied van 250 meter berekend (metrisch CRS: EPSG:28992,
   Amersfoort/RD New).
3. **Gebieden buiten dekking** — het buffergebied wordt van de
   buurtpolygonen afgetrokken (`geopandas.GeoSeries.difference`); wat
   overblijft is het gebied zonder dekking.
4. **Prioriteitsbuurten** — buurten met een bevolkingsdichtheid boven de
   mediaan **én** waarvan minstens 35% van de oppervlakte buiten het
   dekkingsgebied valt.
5. **Kandidaatpunten genereren en scoren** — binnen het onbedekte deel van
   elke prioriteitsbuurt worden willekeurige kandidaatpunten gegenereerd.
   Elk punt krijgt een score van 0-100 op basis van
   `0,45×dichtheid + 0,35×afstand_tot_dichtstbijzijnde_paal + 0,20×aandeel_onbedekt`;
   kandidaten binnen 300 m van een reeds gekozen locatie worden uitgesloten.
6. **Top 10** — de 10 hoogst scorende kandidaten worden weggeschreven naar
   `outputs/top10_kandidaten.csv` en op de interactieve kaart getoond.

## Data verversen

Wil je met een nieuwere versie van de brondata werken (bijvoorbeeld een
recentere OCM-export)? Vervang het betreffende bestand in `data/ruw/` en
draai opnieuw:

```bash
python3 src/verwerk_echte_data.py
cd src && python3 bouw_kaart.py
```


## Licentie

CBS-data: CC-BY 4.0. Open Charge Map-data: open data, community-onderhouden
(zie [openchargemap.org](https://openchargemap.org) voor licentiedetails
per databron). Gemeente Amsterdam buurtdata: zie voorwaarden op
[data.amsterdam.nl](https://data.amsterdam.nl).
