"""

Bronnen:
  1. buurten_amsterdam_lat_lon.json - buurtgrenzen Amsterdam (gemeente
                                       Amsterdam), LET OP: coördinaten staan
                                       als [lat, lon] in plaats van de
                                       GeoJSON-standaard [lon, lat]
  2. cbs_kerncijfers_wijken_buurten.csv - CBS "Kerncijfers wijken en
                                           buurten", met AantalInwoners_5
                                           per buurtcode
  3. laadpalen_ocm.json                 - Open Charge Map export (POI's)
                                           voor Amsterdam, NL

Output (in data/echt/):
  - buurten_amsterdam.geojson
  - ev_laadpalen_bestaand.geojson
"""
import json
import os

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, Polygon, MultiPolygon

HERE = os.path.dirname(__file__)
RUW_DIR = os.path.join(HERE, "..", "data", "ruw")
OUT_DIR = os.path.join(HERE, "..", "data", "echt")
os.makedirs(OUT_DIR, exist_ok=True)

WGS84 = "EPSG:4326"


def swap_coords(coords):
    """Wissel [lat, lon] om naar [lon, lat] (GeoJSON-standaard), recursief."""
    if isinstance(coords[0], (float, int)):
        lat, lon = coords
        return [lon, lat]
    return [swap_coords(c) for c in coords]


def bouw_buurten():
    with open(os.path.join(RUW_DIR, "buurten_amsterdam_lat_lon.json")) as f:
        buurten_raw = json.load(f)

    # CBS-bevolkingstabel inladen en filteren op Amsterdamse buurten
    cbs = pd.read_csv(
        os.path.join(RUW_DIR, "cbs_kerncijfers_wijken_buurten.csv"),
        sep=";", encoding="utf-8-sig"
    )
    cbs.columns = [c.strip() for c in cbs.columns]
    for col in ["WijkenEnBuurten", "Gemeentenaam_1", "SoortRegio_2", "Codering_3", "AantalInwoners_5"]:
        cbs[col] = cbs[col].astype(str).str.strip()
    cbs_buurten = cbs[
        (cbs["Gemeentenaam_1"] == "Amsterdam") & (cbs["SoortRegio_2"] == "Buurt")
    ].copy()
    cbs_buurten["AantalInwoners_5"] = pd.to_numeric(cbs_buurten["AantalInwoners_5"], errors="coerce")
    bevolking_per_code = dict(zip(cbs_buurten["Codering_3"], cbs_buurten["AantalInwoners_5"]))

    rijen = []
    overgeslagen_geen_bevolking = 0
    for feat in buurten_raw["features"]:
        props = feat["properties"]
        geom = feat["geometry"]

        # coördinaten van [lat, lon] naar [lon, lat] omzetten
        gecorrigeerd = swap_coords(geom["coordinates"])
        if geom["type"] == "Polygon":
            polygon = Polygon(gecorrigeerd[0], holes=gecorrigeerd[1:] if len(gecorrigeerd) > 1 else None)
        elif geom["type"] == "MultiPolygon":
            polygon = MultiPolygon([Polygon(p[0], holes=p[1:] if len(p) > 1 else None) for p in gecorrigeerd])
        else:
            continue

        buurtcode = props.get("CBS_Buurtcode")
        bevolking = bevolking_per_code.get(buurtcode)
        if bevolking is None or pd.isna(bevolking):
            overgeslagen_geen_bevolking += 1
            continue

        opp_km2 = props.get("Oppervlakte_m2", 0) / 1_000_000
        if opp_km2 <= 0:
            continue
        dichtheid = bevolking / opp_km2

        rijen.append({
            "buurt_naam": props.get("Buurt", buurtcode),
            "stadsdeel": props.get("Stadsdeel", ""),
            "bevolking": int(bevolking),
            "oppervlakte_km2": round(opp_km2, 4),
            "bev_dichtheid": round(dichtheid, 1),
            "geometry": polygon,
        })

    print(f"{len(rijen)} buurten met bevolkingsdata, {overgeslagen_geen_bevolking} overgeslagen (geen CBS-match)")
    gdf = gpd.GeoDataFrame(rijen, crs=WGS84)
    return gdf


def bouw_laadpalen():
    with open(os.path.join(RUW_DIR, "laadpalen_ocm.json")) as f:
        ocm_data = json.load(f)

    rijen = []
    for poi in ocm_data:
        adres = poi.get("AddressInfo") or {}
        lat, lon = adres.get("Latitude"), adres.get("Longitude")
        if lat is None or lon is None:
            continue
        rijen.append({
            "laadpaal_id": f"OCM-{poi.get('ID')}",
            "aantal_laadpunten": poi.get("NumberOfPoints") or 1,
            "operator_id": poi.get("OperatorID"),
            "adres": adres.get("AddressLine1", ""),
            "geometry": Point(lon, lat),
        })

    gdf = gpd.GeoDataFrame(rijen, crs=WGS84)
    return gdf


def voeg_stadsdeel_toe_aan_laadpalen(laadpalen, buurten):
    """Ken elke laadpaal een buurt/stadsdeel toe via ruimtelijke join."""
    joined = gpd.sjoin(laadpalen, buurten[["buurt_naam", "stadsdeel", "geometry"]], how="left", predicate="within")
    joined = joined.drop(columns=["index_right"])
    return joined


if __name__ == "__main__":
    buurten = bouw_buurten()
    laadpalen = bouw_laadpalen()
    laadpalen = voeg_stadsdeel_toe_aan_laadpalen(laadpalen, buurten)

    # buurt/stadsdeel ontbreekt voor laadpalen buiten alle buurtgrenzen (water, randgebied)
    laadpalen["buurt_naam"] = laadpalen["buurt_naam"].fillna("Onbekend")
    laadpalen["stadsdeel"] = laadpalen["stadsdeel"].fillna("Onbekend")

    buurten.to_file(os.path.join(OUT_DIR, "buurten_amsterdam.geojson"), driver="GeoJSON")
    laadpalen.to_file(os.path.join(OUT_DIR, "ev_laadpalen_bestaand.geojson"), driver="GeoJSON")

    print(f"\nOpgeslagen in {OUT_DIR}:")
    print(f"  buurten_amsterdam.geojson       ({len(buurten)} buurten)")
    print(f"  ev_laadpalen_bestaand.geojson   ({len(laadpalen)} laadpalen)")
    print("\nBevolking per stadsdeel:")
    print(buurten.groupby("stadsdeel")["bevolking"].sum().sort_values(ascending=False))
