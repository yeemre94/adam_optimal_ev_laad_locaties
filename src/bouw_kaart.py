"""
bouw_kaart.py
-------------
Bouwt de uiteindelijke interactieve Folium-kaart: choropleth van de
bevolkingsdichtheid per buurt, bestaande laadpalen, dekkingsgebied van 250
m, en de top-10 aanbevolen locaties.
Uitvoeren: python3 src/bouw_kaart.py
Output: outputs/interactieve_kaart.html
"""
import os

import folium
from folium import Choropleth, FeatureGroup, LayerControl

from analyse import top_n_locaties

HIER = os.path.dirname(__file__)
DATA_DIR = os.path.join(HIER, "..", "data", "echt")
OUTPUT_DIR = os.path.join(HIER, "..", "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

AMSTERDAM_MIDDELPUNT = [52.3676, 4.9041]


def bouw_kaart():
    top10, lagen = top_n_locaties(
        os.path.join(DATA_DIR, "buurten_amsterdam.geojson"),
        os.path.join(DATA_DIR, "ev_laadpalen_bestaand.geojson"),
        n=10,
    )
    buurten = lagen["buurten"]
    laadpalen = lagen["laadpalen"]
    dekking = lagen["dekking"]

    m = folium.Map(location=AMSTERDAM_MIDDELPUNT, zoom_start=12, tiles="CartoDB positron")

    # 1) Choropleth bevolkingsdichtheid
    Choropleth(
        geo_data=buurten.to_json(),
        data=buurten,
        columns=["buurt_naam", "bev_dichtheid"],
        key_on="feature.properties.buurt_naam",
        fill_color="YlOrRd",
        fill_opacity=0.55,
        line_opacity=0.3,
        legend_name="Bevolkingsdichtheid (inwoners/km2)",
        name="Bevolkingsdichtheid",
    ).add_to(m)

    # 2) Dekkingsgebied van 250 m
    dekking_laag = FeatureGroup(name="Dekkingsgebied bestaande laadpalen (250m)", show=True)
    folium.GeoJson(
        dekking.to_json(),
        style_function=lambda x: {"fillColor": "#2b8cbe", "color": "#2b8cbe", "weight": 1, "fillOpacity": 0.25},
    ).add_to(dekking_laag)
    dekking_laag.add_to(m)

    # 3) Bestaande laadpalen
    bestaand_laag = FeatureGroup(name="Bestaande laadpalen", show=True)
    for _, rij in laadpalen.iterrows():
        folium.CircleMarker(
            location=[rij.geometry.y, rij.geometry.x],
            radius=3,
            color="#2b8cbe",
            fill=True,
            fill_opacity=0.8,
            popup=f"{rij['laadpaal_id']} ({rij['aantal_laadpunten']} laadpunten)",
        ).add_to(bestaand_laag)
    bestaand_laag.add_to(m)

    # 4) Top 10 aanbevolen nieuwe locaties
    top10_laag = FeatureGroup(name="Aanbevolen top 10 nieuwe locaties", show=True)
    for _, rij in top10.iterrows():
        folium.Marker(
            location=[rij.geometry.y, rij.geometry.x],
            icon=folium.Icon(color="green", icon="bolt", prefix="fa"),
            popup=folium.Popup(
                f"<b>#{rij['rangorde']} - {rij['buurt_naam']}</b><br>"
                f"Stadsdeel: {rij['stadsdeel']}<br>"
                f"Dichtheid: {rij['bev_dichtheid']:.0f} inw/km2<br>"
                f"Afstand tot dichtstbijzijnde laadpaal: {rij['afstand_tot_dichtstbijzijnde_laadpaal_m']:.0f} m<br>"
                f"Score: {rij['score']:.1f}/100",
                max_width=250,
            ),
        ).add_to(top10_laag)
    top10_laag.add_to(m)

    LayerControl(collapsed=False).add_to(m)

    out_pad = os.path.join(OUTPUT_DIR, "interactieve_kaart.html")
    m.save(out_pad)

    top10_csv_kolommen = ["rangorde", "buurt_naam", "stadsdeel", "bev_dichtheid",
                           "afstand_tot_dichtstbijzijnde_laadpaal_m", "pct_onbedekt", "score"]
    top10_out = top10.copy()
    top10_out["lon"] = top10_out.geometry.x
    top10_out["lat"] = top10_out.geometry.y
    top10_out[top10_csv_kolommen + ["lat", "lon"]].to_csv(
        os.path.join(OUTPUT_DIR, "top10_kandidaten.csv"), index=False
    )

    print("Kaart opgeslagen als outputs/interactieve_kaart.html")
    print("Top 10 CSV opgeslagen als outputs/top10_kandidaten.csv")
    return out_pad


if __name__ == "__main__":
    bouw_kaart()
