# ======================================================================
# Fichier       : photoInsert.py
# Description   : Application Streamlit pour insérer une photo, éditer 
#                 ses métadonnées EXIF (auteur, copyright, description, 
#                 GPS), visualiser la localisation sur une carte, et 
#                 gérer une liste de voyages/destinations.
# Auteur        : Maël Khonde Mbumba | Numéro d’étudiant : 24000486
# Date création : 05/07/2025
# Version       : 1.0
# Licence       : Usage pédagogique (cours OIC)
# Exécution     : Python 3 avec Streamlit
# Usage         : `streamlit run photoInsert.py`
# ======================================================================

import streamlit as st
from PIL import Image
import piexif
import pandas as pd
import folium
from streamlit_folium import st_folium
import requests

# --------- FONCTIONS UTILES ---------

def get_exif_data(img):
    """
    Extrait les métadonnées EXIF d'une image PIL et les retourne sous forme de dictionnaire lisible.
    Affiche un avertissement Streamlit en cas d’erreur sur la lecture du bloc EXIF.
    """
    exif_data = {}
    try:
        if "exif" in img.info:
            exif_dict = piexif.load(img.info["exif"])
            for ifd in exif_dict:
                for tag in exif_dict[ifd]:
                    try:
                        tag_name = piexif.TAGS[ifd][tag]["name"]
                        exif_data[tag_name] = exif_dict[ifd][tag]
                    except KeyError:
                        continue
    except Exception as e:
        st.warning(f"Erreur de lecture EXIF : {e}")
    return exif_data

def deg_to_dms_rational(deg_float):
    """
    Convertit une latitude/longitude en degrés décimaux (float)
    vers le format DMS (degrés, minutes, secondes) attendu par l’EXIF (tuple de rationnels).
    """
    deg = int(deg_float)
    min_float = abs(deg_float - deg) * 60
    min = int(min_float)
    sec = int((min_float - min) * 60 * 100)
    return ((deg, 1), (min, 1), (sec, 100))

def dms_rational_to_deg(dms, ref):
    """
    Convertit une coordonnée GPS EXIF (format DMS rationnel + référence N/S/E/O)
    en degrés décimaux float.
    """
    deg = dms[0][0] / dms[0][1]
    min = dms[1][0] / dms[1][1]
    sec = dms[2][0] / dms[2][1] / 100
    val = deg + min / 60 + sec / 3600
    if ref in ['S', 'W']:
        val = -val
    return val

def get_location_ipapi():
    """
    Récupère la latitude et longitude approximatives via l’API ipapi (géolocalisation IP).
    Retourne (latitude, longitude) ou (None, None) en cas d’échec.
    """
    try:
        response = requests.get('https://ipapi.co/json/')
        if response.status_code == 200:
            data = response.json()
            return data.get('latitude'), data.get('longitude')
    except:
        pass
    return None, None

# --------- APPLICATION STREAMLIT ---------

# Configure la page Streamlit
st.set_page_config(page_title="TP EXIF & Cartographie", layout="wide")
st.title("📷 Manipulation des métadonnées EXIF & cartographie")

# 1. Chargement et édition des métadonnées EXIF
st.header("1. Charger une photo et éditer les métadonnées EXIF")
uploaded_file = st.file_uploader("📂 Chargez une image JPEG", type=["jpg", "jpeg"])

if uploaded_file:
    # Ouvre l’image et affiche un aperçu
    image = Image.open(uploaded_file)
    st.image(image, caption="Aperçu de la photo", use_container_width=True)

    # Lit et affiche les métadonnées EXIF trouvées
    exif_data = get_exif_data(image)
    st.subheader("🔎 Métadonnées EXIF détectées")
    st.json(exif_data)

    # Formulaire Streamlit pour éditer les champs EXIF principaux
    with st.form("edit_exif"):
        st.write("✏️ Modifiez les métadonnées EXIF principales :")
        artist = st.text_input("👤 Artiste / Auteur", value=exif_data.get("Artist", b"").decode(errors="ignore") if exif_data.get("Artist") else "")
        copyright = st.text_input("© Copyright", value=exif_data.get("Copyright", b"").decode(errors="ignore") if exif_data.get("Copyright") else "")
        description = st.text_input("📝 Description", value=exif_data.get("ImageDescription", b"").decode(errors="ignore") if exif_data.get("ImageDescription") else "")
        submitted = st.form_submit_button("💾 Enregistrer les modifications")

    if submitted:
        # Charge ou initialise un dict EXIF, met à jour les champs édités par l'utilisateur
        exif_bytes = image.info.get("exif", None)
        if exif_bytes:
            exif_dict = piexif.load(exif_bytes)
        else:
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

        exif_dict["0th"][piexif.ImageIFD.Artist] = artist.encode('utf-8')
        exif_dict["0th"][piexif.ImageIFD.Copyright] = copyright.encode('utf-8')
        exif_dict["0th"][piexif.ImageIFD.ImageDescription] = description.encode('utf-8')
        exif_bytes_new = piexif.dump(exif_dict)
        image.save("photo_modifiee.jpg", exif=exif_bytes_new)
        st.success("✅ Métadonnées modifiées et image sauvegardée sous 'photo_modifiee.jpg'.")

    # --------- 2. Modification des données GPS ---------

    st.header("2. 🌍 Modifier les coordonnées GPS de la photo")
    lat, lon = get_location_ipapi()
    if lat and lon:
        st.info(f"📍 Votre position actuelle détectée : Latitude {lat:.5f}, Longitude {lon:.5f}")
    else:
        st.warning("❌ Position non détectée automatiquement. Saisissez-la manuellement.")

    with st.form("gps_form"):
        latitude = st.number_input("Latitude", value=lat if lat else 0.0, format="%.6f")
        longitude = st.number_input("Longitude", value=lon if lon else 0.0, format="%.6f")
        gps_submitted = st.form_submit_button("📌 Mettre à jour les coordonnées GPS")

    if gps_submitted:
        # Met à jour la section GPS du dict EXIF et sauvegarde la nouvelle image
        exif_bytes = image.info.get("exif", None)
        if exif_bytes:
            exif_dict = piexif.load(exif_bytes)
        else:
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

        gps_ifd = {
            piexif.GPSIFD.GPSLatitudeRef: b'N' if latitude >= 0 else b'S',
            piexif.GPSIFD.GPSLatitude: deg_to_dms_rational(abs(latitude)),
            piexif.GPSIFD.GPSLongitudeRef: b'E' if longitude >= 0 else b'W',
            piexif.GPSIFD.GPSLongitude: deg_to_dms_rational(abs(longitude)),
        }
        exif_dict['GPS'] = gps_ifd
        exif_bytes = piexif.dump(exif_dict)
        image.save("photo_gps.jpg", exif=exif_bytes)
        st.success("✅ Coordonnées GPS mises à jour et image sauvegardée sous 'photo_gps.jpg'.")

# --------- 3. AFFICHAGE SUR CARTE ---------
st.header("3. 🗺️ Afficher la position GPS de l'image")

try:
    # Ouvre l’image sauvegardée avec GPS ; extrait les coordonnées et affiche la position sur une carte
    image_with_gps = Image.open("photo_gps.jpg")
    exif_bytes = image_with_gps.info.get("exif", None)
    if exif_bytes:
        exif_dict = piexif.load(exif_bytes)
    else:
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

    gps_ifd = exif_dict.get("GPS", {})
    if gps_ifd:
        lat_ref = gps_ifd.get(piexif.GPSIFD.GPSLatitudeRef, b'N').decode() if isinstance(gps_ifd.get(piexif.GPSIFD.GPSLatitudeRef), bytes) else gps_ifd.get(piexif.GPSIFD.GPSLatitudeRef, 'N')
        lat = gps_ifd.get(piexif.GPSIFD.GPSLatitude)
        lon_ref = gps_ifd.get(piexif.GPSIFD.GPSLongitudeRef, b'E').decode() if isinstance(gps_ifd.get(piexif.GPSIFD.GPSLongitudeRef), bytes) else gps_ifd.get(piexif.GPSIFD.GPSLongitudeRef, 'E')
        lon = gps_ifd.get(piexif.GPSIFD.GPSLongitude)
        if lat and lon:
            lat_deg = dms_rational_to_deg(lat, lat_ref)
            lon_deg = dms_rational_to_deg(lon, lon_ref)
            st.map(pd.DataFrame({'lat': [lat_deg], 'lon': [lon_deg]}))
        else:
            st.info("🛈 Aucune coordonnée GPS enregistrée dans cette image.")
    else:
        st.info("🛈 Aucune coordonnée GPS enregistrée dans cette image.")

except Exception as e:
    st.error(f"❌ Erreur de lecture EXIF GPS : {e}")

# --------- 4. GESTION DE LISTE DE DESTINATIONS ---------

st.header("4. 🌟 Vos voyages ou destinations de rêve")
st.write("Ajoutez des lieux (nom, latitude, longitude).")

# Liste d’exemples de lieux, éditable par l'utilisateur
default_poi = [
    {"nom": "Paris", "latitude": 48.8566, "longitude": 2.3522},
    {"nom": "Tokyo", "latitude": 35.6895, "longitude": 139.6917},
    {"nom": "New York", "latitude": 40.7128, "longitude": -74.0060},
]
poi_df = pd.DataFrame(default_poi)

# Tableur interactif Streamlit pour entrer/modifier la liste
poi_input = st.data_editor(poi_df, num_rows="dynamic", key="poi_editor")

# Nettoie la liste des points (supprime les lignes incomplètes)
poi_input_clean = poi_input.dropna(subset=["latitude", "longitude"])

if len(poi_input_clean) >= 2:
    # Affiche la liste sur une carte, trace un trajet entre les points
    m = folium.Map(location=[poi_input_clean.iloc[0]["latitude"], poi_input_clean.iloc[0]["longitude"]], zoom_start=2)
    points = []
    for idx, row in poi_input_clean.iterrows():
        folium.Marker([row["latitude"], row["longitude"]], popup=row["nom"]).add_to(m)
        points.append((row["latitude"], row["longitude"]))
    folium.PolyLine(points, color="blue", weight=15, opacity=1).add_to(m)
    st_folium(m, width=700)
else:
    st.info("➕ Ajoutez au moins deux destinations valides pour visualiser la carte.")
