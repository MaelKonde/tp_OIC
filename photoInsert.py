#======================================================================
# Nom du fichier   : photoInsert.py
# Rôle             : Insertion d’une photo et édition des métadonnées EXIF
# Auteur           : Maël Khonde Mbumba | Numéro d’étudiant : 24000486
# Date de création : 05/03/2025
# Version          : 1.0
# Licence          : Exercice dans le cadre du cours de OIC
# Compilation.     : (Pas de compilation, interprété avec Python 3)
# Usage            : Pour exécuter : photoInsert.py               
# =====================================================================
import streamlit as st
from PIL import Image
import piexif
import folium
from streamlit_folium import st_folium
import io
import pandas as pd
import json

# === Fonctions utilitaires ===

def deg_to_dms_rational(deg_float):
    min_float = (deg_float - int(deg_float)) * 60
    sec_float = (min_float - int(min_float)) * 60
    return [
        (int(deg_float), 1),
        (int(min_float), 1),
        (int(sec_float * 100), 100)
    ]

def dms_to_deg(value):
    d, m, s = value
    return d[0]/d[1] + m[0]/m[1]/60 + s[0]/s[1]/3600

def extract_gps_data(exif_dict):
    gps = exif_dict.get("GPS", {})
    if gps:
        lat = dms_to_deg(gps.get(piexif.GPSIFD.GPSLatitude, [(0,1),(0,1),(0,1)]))
        lon = dms_to_deg(gps.get(piexif.GPSIFD.GPSLongitude, [(0,1),(0,1),(0,1)]))
        lat_ref = gps.get(piexif.GPSIFD.GPSLatitudeRef, b"N").decode()
        lon_ref = gps.get(piexif.GPSIFD.GPSLongitudeRef, b"E").decode()
        if lat_ref == "S":
            lat = -lat
        if lon_ref == "W":
            lon = -lon
        return lat, lon
    return None, None

def save_image_with_exif(img, exif_dict):
    exif_bytes = piexif.dump(exif_dict)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", exif=exif_bytes)
    buffer.seek(0)
    return buffer

def auto_zoom(lat):
    if abs(lat) > 60:
        return 4
    elif abs(lat) > 30:
        return 6
    else:
        return 10

# === Titre ===
st.title("🖼️ Modification des métadonnées GPS & EXIF d'une image")

# === Image upload ===
uploaded_file = st.file_uploader("📤 Importer une image JPEG", type=["jpg", "jpeg"])
if uploaded_file:
    img = Image.open(uploaded_file)
    st.image(img, caption="Image importée", use_column_width=True)

    exif_dict = piexif.load(img.info.get("exif", b"")) if "exif" in img.info else {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
    lat_img, lon_img = extract_gps_data(exif_dict)

    st.subheader("📄 Métadonnées EXIF actuelles")
    st.json(exif_dict)

    if lat_img is not None and lon_img is not None:
        st.success(f"✅ L’image contient des coordonnées GPS : Latitude={lat_img:.6f}, Longitude={lon_img:.6f}")
    else:
        st.warning("⚠️ L’image ne contient aucune coordonnées GPS.")

    lat_current = 48.9601  # Meaux
    lon_current = 2.8787

    st.subheader("📍 Modifier les coordonnées GPS")
    lat_input = st.number_input("Nouvelle latitude", value=lat_img if lat_img is not None else lat_current, format="%.6f")
    lon_input = st.number_input("Nouvelle longitude", value=lon_img if lon_img is not None else lon_current, format="%.6f")

    if st.button("💾 Enregistrer coordonnées et métadonnées"):
        gps_ifd = {
            piexif.GPSIFD.GPSLatitudeRef: b"N" if lat_input >= 0 else b"S",
            piexif.GPSIFD.GPSLatitude: deg_to_dms_rational(abs(lat_input)),
            piexif.GPSIFD.GPSLongitudeRef: b"E" if lon_input >= 0 else b"W",
            piexif.GPSIFD.GPSLongitude: deg_to_dms_rational(abs(lon_input)),
        }
        exif_dict["GPS"] = gps_ifd

        # === Formulaire EXIF professionnel ===
        st.subheader("📝 Formulaire métadonnées EXIF (professionnel)")
        make = st.text_input("Appareil (Make)", exif_dict["0th"].get(piexif.ImageIFD.Make, b"").decode(errors="ignore"))
        model = st.text_input("Modèle (Model)", exif_dict["0th"].get(piexif.ImageIFD.Model, b"").decode(errors="ignore"))
        artist = st.text_input("Auteur/Artiste", exif_dict["0th"].get(piexif.ImageIFD.Artist, b"").decode(errors="ignore"))
        software = st.text_input("Logiciel utilisé", exif_dict["0th"].get(piexif.ImageIFD.Software, b"").decode(errors="ignore"))

        exif_dict["0th"][piexif.ImageIFD.Make] = make.encode("utf-8")
        exif_dict["0th"][piexif.ImageIFD.Model] = model.encode("utf-8")
        exif_dict["0th"][piexif.ImageIFD.Artist] = artist.encode("utf-8")
        exif_dict["0th"][piexif.ImageIFD.Software] = software.encode("utf-8")

        buffer = save_image_with_exif(img, exif_dict)
        match = abs(lat_input - lat_current) < 0.001 and abs(lon_input - lon_current) < 0.001

        if match:
            st.success("✅ Coordonnées saisies correspondent à votre position actuelle (Meaux).")
        else:
            st.warning("❌ Coordonnées saisies différentes de votre position actuelle.")

        st.download_button("📥 Télécharger l’image modifiée", data=buffer, file_name="image_modifiee.jpg", mime="image/jpeg")

    # === Carte ===
    st.subheader("🗺️ Carte des coordonnées")
    map_center = [lat_current, lon_current]
    m = folium.Map(location=map_center, zoom_start=6)
    folium.Marker([lat_current, lon_current], tooltip="Ma position actuelle (Meaux)", icon=folium.Icon(color="green")).add_to(m)
    folium.Marker([lat_input, lon_input], tooltip="Coordonnées saisies", icon=folium.Icon(color="blue")).add_to(m)
    st_folium(m, width=700)

# === Section POI ===
st.header("4. POI : voyages ou destinations de rêve")
default_poi = [
    {"nom": "Paris", "latitude": 48.8566, "longitude": 2.3522},
    {"nom": "Kinshasa", "latitude": -4.4419, "longitude": 15.2663},
    {"nom": "Luxembourg", "latitude": 49.6117, "longitude": 6.1319},
    {"nom": "Bruxelles", "latitude": 50.8503, "longitude": 4.3517},
    {"nom": "Karlsruhe", "latitude": 49.0069, "longitude": 8.4037},
    {"nom": "Dortmund", "latitude": 51.5136, "longitude": 7.4653},
]

poi_df = pd.DataFrame(default_poi)
poi_input = st.data_editor(poi_df, num_rows="dynamic", key="poi_editor")
if len(poi_input) >= 2:
    center = [poi_input.iloc[0]["latitude"], poi_input.iloc[0]["longitude"]]
    voyage_map = folium.Map(location=center, zoom_start=3)
    pts = []
    for _, r in poi_input.iterrows():
        folium.Marker([r.latitude, r.longitude], popup=r.nom).add_to(voyage_map)
        pts.append((r.latitude, r.longitude))
    folium.PolyLine(pts, color="blue").add_to(voyage_map)
    st.subheader("🗺️ Carte des POI")
    st_folium(voyage_map, width=700)
else:
    st.info("Ajoute au moins deux lieux 😊")
