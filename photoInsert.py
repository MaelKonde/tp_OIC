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
import pandas as pd
import folium
from streamlit_folium import st_folium
import requests
from io import BytesIO

# --------- CONFIGURATION DE LA PAGE ---------
st.set_page_config(page_title="TP EXIF & Cartographie", layout="wide")
st.title("📸 Manipulation EXIF & Cartographie interactive")

# --------- FONCTIONS UTILES ---------

def get_exif_data(img):
    """Retourne les données EXIF sous forme de dictionnaire lisible."""
    exif_data = {}
    if "exif" in img.info:
        exif_dict = piexif.load(img.info["exif"])
        for ifd in exif_dict:
            for tag in exif_dict[ifd]:
                try:
                    tag_name = piexif.TAGS[ifd][tag]["name"]
                    exif_data[tag_name] = exif_dict[ifd][tag]
                except KeyError:
                    continue
    return exif_data

def deg_to_dms_rational(deg_float):
    """Convertit un float degré GPS en format DMS rationnel (tuple pour EXIF)."""
    deg = int(deg_float)
    min_float = abs(deg_float - deg) * 60
    min_ = int(min_float)
    sec = int((min_float - min_) * 60 * 100)
    return ((deg, 1), (min_, 1), (sec, 100))

def dms_rational_to_deg(dms, ref):
    """Convertit DMS EXIF en degré décimal."""
    deg = dms[0][0] / dms[0][1]
    min_ = dms[1][0] / dms[1][1]
    sec = dms[2][0] / dms[2][1] / 100
    val = deg + min_ / 60 + sec / 3600
    if ref in ['S', 'W']:
        val = -val
    return val

def get_location_ipapi():
    """Détecte la position géographique via IP (API ipapi)."""
    try:
        response = requests.get('https://ipapi.co/json/')
        if response.status_code == 200:
            data = response.json()
            return data.get('latitude'), data.get('longitude')
    except:
        pass
    return None, None

# --------- 1. CHARGEMENT IMAGE & METADONNEES ---------

st.header("1️⃣ Charger une image et modifier les métadonnées EXIF")
uploaded_file = st.file_uploader("📷 Charger une photo (JPEG uniquement)", type=["jpg", "jpeg"])

if uploaded_file:
    image = Image.open(uploaded_file)

    st.image(image, caption="Aperçu de l'image", use_column_width=True)

    # Extraction des métadonnées existantes
    exif_data = get_exif_data(image)
    st.subheader("📑 Métadonnées EXIF détectées")
    st.json(exif_data)

    with st.form("form_exif"):
        st.write("📝 Modifier les champs EXIF suivants :")
        artist = st.text_input("Auteur / Artiste", value=exif_data.get("Artist", b"").decode(errors="ignore") if exif_data.get("Artist") else "")
        copyright = st.text_input("Copyright", value=exif_data.get("Copyright", b"").decode(errors="ignore") if exif_data.get("Copyright") else "")
        description = st.text_input("Description", value=exif_data.get("ImageDescription", b"").decode(errors="ignore") if exif_data.get("ImageDescription") else "")
        exif_submit = st.form_submit_button("💾 Enregistrer les métadonnées")

    if exif_submit:
        exif_dict = piexif.load(image.info["exif"]) if "exif" in image.info else {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
        exif_dict["0th"][piexif.ImageIFD.Artist] = artist.encode('utf-8')
        exif_dict["0th"][piexif.ImageIFD.Copyright] = copyright.encode('utf-8')
        exif_dict["0th"][piexif.ImageIFD.ImageDescription] = description.encode('utf-8')
        exif_bytes = piexif.dump(exif_dict)
        
        output = BytesIO()
        image.save(output, format="JPEG", exif=exif_bytes)
        st.success("✅ Métadonnées modifiées avec succès !")
        st.download_button("📥 Télécharger l'image modifiée", data=output.getvalue(), file_name="image_modifiee.jpg", mime="image/jpeg")

    # --------- 2. MODIFICATION GPS ---------
    st.header("2️⃣ Ajouter ou modifier les coordonnées GPS")
    lat, lon = get_location_ipapi()
    if lat and lon:
        st.info(f"📍 Position détectée : {lat:.5f}, {lon:.5f}")
    else:
        st.warning("⚠️ Impossible de détecter automatiquement votre position.")

    with st.form("form_gps"):
        latitude = st.number_input("Latitude", value=lat if lat else 0.0, format="%.6f")
        longitude = st.number_input("Longitude", value=lon if lon else 0.0, format="%.6f")
        gps_submit = st.form_submit_button("📌 Mettre à jour les coordonnées GPS")

    if gps_submit:
        exif_dict = piexif.load(image.info["exif"]) if "exif" in image.info else {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
        gps_ifd = {
            piexif.GPSIFD.GPSLatitudeRef: b'N' if latitude >= 0 else b'S',
            piexif.GPSIFD.GPSLatitude: deg_to_dms_rational(abs(latitude)),
            piexif.GPSIFD.GPSLongitudeRef: b'E' if longitude >= 0 else b'W',
            piexif.GPSIFD.GPSLongitude: deg_to_dms_rational(abs(longitude)),
        }
        exif_dict['GPS'] = gps_ifd
        exif_bytes = piexif.dump(exif_dict)

        output = BytesIO()
        image.save(output, format="JPEG", exif=exif_bytes)
        st.success("✅ Coordonnées GPS mises à jour !")
        st.download_button("📥 Télécharger l'image avec GPS", data=output.getvalue(), file_name="image_gps.jpg", mime="image/jpeg")

    # --------- 3. AFFICHAGE SUR CARTE ---------
    st.header("3️⃣ Afficher la localisation GPS sur carte")
    try:
        gps_info = piexif.load(image.info["exif"]).get("GPS")
        if gps_info:
            lat_ref = gps_info[piexif.GPSIFD.GPSLatitudeRef].decode()
            lon_ref = gps_info[piexif.GPSIFD.GPSLongitudeRef].decode()
            lat_dms = gps_info[piexif.GPSIFD.GPSLatitude]
            lon_dms = gps_info[piexif.GPSIFD.GPSLongitude]
            lat_img = dms_rational_to_deg(lat_dms, lat_ref)
            lon_img = dms_rational_to_deg(lon_dms, lon_ref)
            st.map(pd.DataFrame({'lat': [lat_img], 'lon': [lon_img]}))
        else:
            st.info("📭 Aucun GPS tag détecté dans l'image.")
    except Exception as e:
        st.warning(f"Erreur de lecture EXIF GPS : {e}")

  # --------- 4. AFFICHAGE DES POI (VOYAGES/RÊVES) ---------
st.header("4️⃣ Vos voyages ou destinations de rêve")
st.write("Ajoutez des lieux (nom, latitude, longitude).")

# Exemple de POI par défaut
default_poi = [
    {"nom": "Paris", "latitude": 48.8566, "longitude": 2.3522},
    {"nom": "Tokyo", "latitude": 35.6895, "longitude": 139.6917},
    {"nom": "New York", "latitude": 40.7128, "longitude": -74.0060},
]
poi_df = pd.DataFrame(default_poi)

# ✅ version stable de l'éditeur de données
poi_input = st.data_editor(poi_df, num_rows="dynamic", key="poi_editor")

# Affichage de la carte avec POIs
if len(poi_input) >= 2:
    m = folium.Map(location=[poi_input.iloc[0]["latitude"], poi_input.iloc[0]["longitude"]], zoom_start=2)
    points = []
    for idx, row in poi_input.iterrows():
        folium.Marker([row["latitude"], row["longitude"]], popup=row["nom"]).add_to(m)
        points.append((row["latitude"], row["longitude"]))
    folium.PolyLine(points, color="blue", weight=2.5, opacity=1).add_to(m)
    st_folium(m, width=700)
else:
    st.info("Ajoutez au moins deux destinations pour afficher la carte.")
