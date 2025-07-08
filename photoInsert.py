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
import pandas as pd  # ⚠️ requis pour la section POI

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

    # Position actuelle par défaut
    lat_current = 48.8566  # Paris
    lon_current = 2.3522

    # États session initiaux
    st.session_state.setdefault("lat", lat_img if lat_img else lat_current)
    st.session_state.setdefault("lon", lon_img if lon_img else lon_current)
    st.session_state.setdefault("modified_image", None)
    st.session_state.setdefault("show_lat", lat_img)
    st.session_state.setdefault("show_lon", lon_img)

    # === GPS ===

    st.subheader("📍 Modifier les coordonnées GPS")
    st.session_state.lat = st.number_input("Latitude", value=st.session_state.lat, format="%.6f")
    st.session_state.lon = st.number_input("Longitude", value=st.session_state.lon, format="%.6f")

    if abs(st.session_state.lat - lat_current) < 0.001 and abs(st.session_state.lon - lon_current) < 0.001:
        st.success("✅ Coordonnées correspondent à ta position actuelle.")
    else:
        st.warning("ℹ️ Coordonnées saisies différentes de ta position actuelle.")

    if st.button("📌 Mettre à jour les coordonnées GPS"):
        gps_ifd = {
            piexif.GPSIFD.GPSLatitudeRef: b"N" if st.session_state.lat >= 0 else b"S",
            piexif.GPSIFD.GPSLatitude: deg_to_dms_rational(abs(st.session_state.lat)),
            piexif.GPSIFD.GPSLongitudeRef: b"E" if st.session_state.lon >= 0 else b"W",
            piexif.GPSIFD.GPSLongitude: deg_to_dms_rational(abs(st.session_state.lon)),
        }
        exif_dict["GPS"] = gps_ifd
        buffer = save_image_with_exif(img, exif_dict)

        st.session_state.modified_image = buffer
        st.session_state.show_lat = st.session_state.lat
        st.session_state.show_lon = st.session_state.lon
        st.success("✅ Coordonnées GPS mises à jour.")

    # === Téléchargement image GPS ===
    if st.session_state.modified_image:
        st.download_button(
            label="📥 Télécharger image GPS",
            data=st.session_state.modified_image,
            file_name="image_gps.jpg",
            mime="image/jpeg"
        )

    # === Carte ===
    if st.session_state.show_lat is not None and st.session_state.show_lon is not None:
        zoom = auto_zoom(st.session_state.show_lat)
        m = folium.Map(location=[st.session_state.show_lat, st.session_state.show_lon], zoom_start=zoom)
        folium.Marker([st.session_state.show_lat, st.session_state.show_lon], popup="Position GPS").add_to(m)
        st.subheader("🗺️ Carte de la position GPS")
        st_folium(m, width=700)

    # === Métadonnées EXIF ===

    st.subheader("📝 Formulaire métadonnées EXIF")
    make = st.text_input("Appareil (Make)", exif_dict["0th"].get(piexif.ImageIFD.Make, b"").decode(errors="ignore"))
    model = st.text_input("Modèle (Model)", exif_dict["0th"].get(piexif.ImageIFD.Model, b"").decode(errors="ignore"))

    if st.button("💾 Enregistrer métadonnées"):
        exif_dict["0th"][piexif.ImageIFD.Make] = make.encode("utf-8")
        exif_dict["0th"][piexif.ImageIFD.Model] = model.encode("utf-8")
        buffer = save_image_with_exif(img, exif_dict)
        st.download_button("📥 Télécharger image modifiée (EXIF)", data=buffer, file_name="image_exif.jpg", mime="image/jpeg")
        st.success("✅ Métadonnées enregistrées.")

    # === SECTION POI ===

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
