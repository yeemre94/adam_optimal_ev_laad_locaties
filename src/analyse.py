"""
analyse.py
----------
Kernanalyse (GeoPandas) voor "Optimale Locaties voor EV-Laadpalen in
Amsterdam".

Uitgevoerde stappen (conform de opdracht):
  1. Buurten, bestaande laadpalen en bevolkingsdichtheid inladen
  2. Bestaande laadpalen bufferen met 250 m (dekkingsgebied)
  3. Gebieden BUITEN de buffer opsporen (onbedekt)
  4. Buurten met hoge bevolkingsdichtheid zonder laadpaal in de buurt
     identificeren
  5. Kandidaatpunten genereren & scoren -> top 10 teruggeven

Alle geometriebewerkingen gebeuren in EPSG:28992 (Amersfoort/RD New, het
Nederlandse metrische rijksdriehoeksstelsel) zodat "250 m" een echte
metrische afstand is, waarna de resultaten worden teruggeprojecteerd naar
EPSG:4326 (lat/lon) voor de kaartweergave.
"""

import geopandas as gpd
import numpy as np
from shapely.geometry import Point

WGS84 = "EPSG:4326"
RD_NEW = "EPSG:28992"  # Nederlands rijksdriehoeksstelsel, eenheid = meters
BUFFER_M = 250


def laad_data(buurten_pad: str, laadpalen_pad: str):
    buurten = gpd.read_file(buurten_pad).to_crs(WGS84)
    laadpalen = gpd.read_file(laadpalen_pad).to_crs(WGS84)
    return buurten, laadpalen


def buffer_bestaande_laadpalen(laadpalen: gpd.GeoDataFrame, buffer_m: int = BUFFER_M):
    """Stap 3: buffer van 250 m rond elke bestaande laadpaal, samengevoegd tot één dekkingspolygoon."""
    laadpalen_metrisch = laadpalen.to_crs(RD_NEW)
    gebufferd = laadpalen_metrisch.buffer(buffer_m)
    dekking = gpd.GeoDataFrame(geometry=[gebufferd.union_all()], crs=RD_NEW).to_crs(WGS84)
    return dekking


def onbedekt_gebied(buurten: gpd.GeoDataFrame, dekking: gpd.GeoDataFrame):
    """Stap 3b: buurtgeometrie min het dekkingsgebied van 250 m = onderbediend gebied."""
    dekking_union = dekking.geometry.iloc[0]
    onbedekt = buurten.copy()
    onbedekt["geometry"] = onbedekt.geometry.difference(dekking_union)
    onbedekt["onbedekt_opp_m2"] = onbedekt.to_crs(RD_NEW).geometry.area
    onbedekt["totaal_opp_m2"] = buurten.to_crs(RD_NEW).geometry.area.values
    onbedekt["pct_onbedekt"] = (onbedekt["onbedekt_opp_m2"] / onbedekt["totaal_opp_m2"] * 100).round(1)
    return onbedekt


def bepaal_prioriteitsbuurten(buurten_met_gat: gpd.GeoDataFrame,
                               dichtheid_percentiel: float = 0.4,
                               min_pct_onbedekt: float = 35.0):
    """
    Stap 3c: buurten met een hoge bevolkingsdichtheid die grotendeels buiten
    de dekking van 250 m vallen -> prioriteitslijst voor nieuwe laadpalen.
    """
    dichtheid_drempel = buurten_met_gat["bev_dichtheid"].quantile(dichtheid_percentiel)
    prioriteit = buurten_met_gat[
        (buurten_met_gat["bev_dichtheid"] >= dichtheid_drempel)
        & (buurten_met_gat["pct_onbedekt"] >= min_pct_onbedekt)
    ].copy()
    return prioriteit.sort_values("bev_dichtheid", ascending=False)


def genereer_kandidaatpunten(prioriteitsbuurten: gpd.GeoDataFrame, punten_per_buurt: int = 3, seed: int = 42):
    """
    Genereer kandidaat-laadpaallocaties binnen het onbedekte deel van elke
    prioriteitsbuurt (willekeurige punten, beperkt tot de onbedekte polygoon).
    """
    rng = np.random.default_rng(seed)
    kandidaten = []
    for _, buurt in prioriteitsbuurten.iterrows():
        geom = buurt.geometry
        if geom.is_empty:
            continue
        minx, miny, maxx, maxy = geom.bounds
        gevonden = 0
        pogingen = 0
        while gevonden < punten_per_buurt and pogingen < 200:
            pogingen += 1
            p = Point(rng.uniform(minx, maxx), rng.uniform(miny, maxy))
            if geom.contains(p):
                kandidaten.append({
                    "buurt_naam": buurt["buurt_naam"],
                    "stadsdeel": buurt["stadsdeel"],
                    "bev_dichtheid": buurt["bev_dichtheid"],
                    "pct_onbedekt": buurt["pct_onbedekt"],
                    "geometry": p,
                })
                gevonden += 1
    return gpd.GeoDataFrame(kandidaten, crs=WGS84)


def score_kandidaten(kandidaten: gpd.GeoDataFrame, laadpalen: gpd.GeoDataFrame):
    """
    Score elke kandidaat: hogere bevolkingsdichtheid + verder van de
    dichtstbijzijnde bestaande laadpaal (tot een maximum) + hoger
    onbedekt-percentage in de buurt = beter. Retourneert de kandidaten met
    een 'score'-kolom van 0-100, gesorteerd op rangorde.
    """
    if kandidaten.empty:
        return kandidaten.assign(afstand_tot_dichtstbijzijnde_laadpaal_m=[], score=[])

    kand_metrisch = kandidaten.to_crs(RD_NEW)
    laadpalen_metrisch = laadpalen.to_crs(RD_NEW)
    laadpalen_union = laadpalen_metrisch.geometry.union_all()

    afstanden = kand_metrisch.geometry.apply(lambda p: p.distance(laadpalen_union))
    kandidaten = kandidaten.copy()
    kandidaten["afstand_tot_dichtstbijzijnde_laadpaal_m"] = afstanden.round(1)

    # normaliseer elke factor naar 0-1
    dichtheid_norm = (kandidaten["bev_dichtheid"] - kandidaten["bev_dichtheid"].min()) / (
        kandidaten["bev_dichtheid"].max() - kandidaten["bev_dichtheid"].min() + 1e-9
    )
    afstand_max = kandidaten["afstand_tot_dichtstbijzijnde_laadpaal_m"].clip(upper=1500)
    afstand_norm = (afstand_max - afstand_max.min()) / (afstand_max.max() - afstand_max.min() + 1e-9)
    dekking_norm = kandidaten["pct_onbedekt"] / 100

    kandidaten["score"] = (0.45 * dichtheid_norm + 0.35 * afstand_norm + 0.20 * dekking_norm) * 100
    kandidaten["score"] = kandidaten["score"].round(1)
    return kandidaten.sort_values("score", ascending=False)


def verwijder_te_dichtbij(gerangschikte_kandidaten: gpd.GeoDataFrame, min_afstand_m: float = 300):
    """Greedy filter: houd de best scorende kandidaat aan, verwijder latere kandidaten binnen min_afstand_m van een behouden punt."""
    behouden_rijen = []
    behouden_geometrieen_metrisch = []
    gerangschikt_metrisch = gerangschikte_kandidaten.to_crs(RD_NEW)
    for (idx, rij), (_, rij_m) in zip(gerangschikte_kandidaten.iterrows(), gerangschikt_metrisch.iterrows()):
        te_dichtbij = any(rij_m.geometry.distance(g) < min_afstand_m for g in behouden_geometrieen_metrisch)
        if not te_dichtbij:
            behouden_rijen.append(rij)
            behouden_geometrieen_metrisch.append(rij_m.geometry)
    return gpd.GeoDataFrame(behouden_rijen, crs=gerangschikte_kandidaten.crs)


def top_n_locaties(buurten_pad: str, laadpalen_pad: str, n: int = 10):
    """End-to-end pipeline: geeft de top-N aanbevolen nieuwe laadpaallocaties terug."""
    buurten, laadpalen = laad_data(buurten_pad, laadpalen_pad)
    dekking = buffer_bestaande_laadpalen(laadpalen, BUFFER_M)
    gat = onbedekt_gebied(buurten, dekking)
    prioriteit = bepaal_prioriteitsbuurten(gat)
    kandidaten = genereer_kandidaatpunten(prioriteit, punten_per_buurt=4)
    gescoord = score_kandidaten(kandidaten, laadpalen)
    gespreid = verwijder_te_dichtbij(gescoord, min_afstand_m=300)
    top = gespreid.head(n).reset_index(drop=True)
    top.insert(0, "rangorde", range(1, len(top) + 1))
    return top, {"buurten": buurten, "laadpalen": laadpalen, "dekking": dekking, "gat": gat, "prioriteit": prioriteit}
