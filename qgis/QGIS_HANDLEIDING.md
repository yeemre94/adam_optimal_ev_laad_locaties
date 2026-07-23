# QGIS-installatie en analysestappen

De `.geojson`- en `.csv`-bestanden in deze repo kun je ook in QGIS openen om
dezelfde analyse visueel/interactief uit te voeren. Onderstaande stappen
gelden voor QGIS 3.x (menu Layer > Add Layer).

## 1. Lagen toevoegen

Voeg via `Layer > Add Layer > Add Vector Layer` achtereenvolgens toe:

| Bestand | Laagnaam | Inhoud |
|---|---|---|
| `data/echt/buurten_amsterdam.geojson` | Buurten | Grenzen + bevolkingsdichtheid (`bev_dichtheid`) |
| `data/echt/ev_laadpalen_bestaand.geojson` | Bestaande Laadpalen | Puntenlaag |
| `outputs/top10_kandidaten.csv` | Aanbevolen Nieuwe Locaties | `Layer > Add Layer > Add Delimited Text Layer`, X-veld = `lon`, Y-veld = `lat`, CRS = EPSG:4326 |

## 2. Lagen met verschillende kleuren tonen

- **Buurten**: rechtermuisklik > Properties > Symbology > kies `Graduated`,
  Value = `bev_dichtheid`, kleurenschaal = `YlOrRd`, 5 klassen (Natural
  Breaks/Jenks).
- **Bestaande Laadpalen**: `Single Symbol`, blauwe cirkel, grootte 2mm.
- **Aanbevolen Nieuwe Locaties**: `Single Symbol`, groen stersymbool,
  grootte 4mm; voeg een label toe (stel het veld `rangorde` in als label
  via Layer Properties > Labels).

## 3. Analyse (Vector-gereedschapskist)

1. **Buffer**: `Vector > Geoprocessing Tools > Buffer`
   - Input: Bestaande Laadpalen
   - Distance: `250` (zet eerst het CRS van de laag naar EPSG:28992 -
     Amersfoort / RD New, zodat je in meters werkt:
     `Layer > CRS > Set Layer CRS`)
   - Dissolve result: ja
   - Output: `laadpaal_dekking_250m`

2. **Gebieden buiten de buffer**: `Vector > Geoprocessing Tools > Difference`
   - Input: Buurten
   - Overlay: `laadpaal_dekking_250m`
   - Output: `gebieden_zonder_dekking`

3. **Buurten met hoge dichtheid + zonder dekking**: pas op de laag
   `gebieden_zonder_dekking` een `Filter` toe (rechtermuisklik > Filter):
   ```sql
   "bev_dichtheid" > (SELECT avg("bev_dichtheid") FROM buurten_amsterdam)
   ```
   of gebruik de Field Calculator om het oppervlaktepercentage te
   berekenen (`$area / totale_buurtoppervlakte`).

4. Exporteer de resultaten via `Project > Import/Export > Export Map to
   Image` als PNG, of maak een PDF-rapport via `Project > New Print
   Layout`.

## Opmerking

Dezelfde analyse wordt in `notebooks/ev_laadpaal_analyse.ipynb` automatisch
en herhaalbaar uitgevoerd met Python/GeoPandas — de QGIS-stappen dienen
vooral voor visuele verificatie en presentatie. Om een `.qgz`-projectbestand
te maken, open je de QGIS-desktopapplicatie, voeg je bovenstaande lagen toe
en sla je op via `Project > Save As` (in deze omgeving kan de
QGIS-desktopapplicatie niet worden uitgevoerd, dus er is geen kant-en-klaar
`.qgz`-bestand meegeleverd).
