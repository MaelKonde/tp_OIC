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

# --------- FONCTIONS UTILES ---------

def get_exif_data(img):
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
    deg = int(deg_float)
    min_float = abs(deg_float - deg) * 60
    min = int(min_float)
    sec = int((min_float - min) * 60 * 100)
    return ((deg, 1), (min, 1), (sec, 100))

def dms_rational_to_deg(dms, ref):
    deg = dms[0][0] / dms[0][1]
    min = dms[1][0] / dms[1][1]
    sec = dms[2][0] / dms[2][1] / 100
    val = deg + min / 60 + sec / 3600
    if ref in ['S', 'W']:
        val = -val
    return val

def get_location_ipapi():
    try:
        response = requests.get('https://ipapi.co/json/')
        if response.status_code == 200:
            data = response.json()
            return data.get('latitude'), data.get('longitude')
    except:
        pass
    return None, None

# --------- APPLICATION STREAMLIT ---------

st.set_page_config(page_title="TP EXIF & Cartographie", layout="wide")
st.title("Manipulation des métadonnées EXIF et cartographie")

st.header("1. Charger une photo et éditer les métadonnées EXIF")
uploaded_file = st.file_uploader("Chargez une photo (JPEG uniquement)", type=["jpg", "jpeg"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Aperçu de la photo", use_column_width=True)

    # Extraction des métadonnées EXIF existantes
    exif_data = get_exif_data(image)
    st.subheader("Métadonnées EXIF détectées")
    st.json(exif_data)

    # Formulaire pour éditer les métadonnées EXIF principales
    with st.form("edit_exif"):
        st.write("Modifiez les métadonnées EXIF principales :")
        artist = st.text_input("Artiste / Auteur", value=exif_data.get("Artist", b"").decode(errors="ignore") if exif_data.get("Artist") else "")
        copyright = st.text_input("Copyright", value=exif_data.get("Copyright", b"").decode(errors="ignore") if exif_data.get("Copyright") else "")
        description = st.text_input("Description", value=exif_data.get("ImageDescription", b"").decode(errors="ignore") if exif_data.get("ImageDescription") else "")
        submitted = st.form_submit_button("Enregistrer les modifications")

    if submitted:
        exif_dict = piexif.load(image.info["exif"]) if "exif" in image.info else piexif.load(piexif.dump({}))
        exif_dict["0th"][piexif.ImageIFD.Artist] = artist.encode('utf-8')
        exif_dict["0th"][piexif.ImageIFD.Copyright] = copyright.encode('utf-8')
        exif_dict["0th"][piexif.ImageIFD.ImageDescription] = description.encode('utf-8')
        exif_bytes = piexif.dump(exif_dict)
        image.save("photo_modifiee.jpg", exif=exif_bytes)
        st.success("Métadonnées EXIF modifiées et image sauvegardée sous 'photo_modifiee.jpg'.")

        # Ajout bouton téléchargement PNG
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        st.download_button(
            label="📥 Télécharger l'image modifiée en PNG",
            data=buffer,
            file_name="photo_modifiee.png",
            mime="image/png"
        )

    # --------- 2. MODIFIER LES DONNÉES GPS ---------
    st.header("2. Modifier les coordonnées GPS de la photo")
    lat, lon = get_location_ipapi()
    if lat and lon:
        st.info(f"Votre position actuelle détectée : Latitude {lat:.5f}, Longitude {lon:.5f}")
    else:
        st.warning("Impossible de détecter automatiquement votre position. Saisissez-la manuellement.")

    with st.form("gps_form"):
        latitude = st.number_input("Latitude", value=lat if lat else 0.0, format="%.6f")
        longitude = st.number_input("Longitude", value=lon if lon else 0.0, format="%.6f")
        gps_submitted = st.form_submit_button("Mettre à jour les coordonnées GPS")

    if gps_submitted:
        exif_dict = piexif.load(image.info["exif"]) if "exif" in image.info else piexif.load(piexif.dump({}))
        gps_ifd = {
            piexif.GPSIFD.GPSLatitudeRef: b'N' if latitude >= 0 else b'S',
            piexif.GPSIFD.GPSLatitude: deg_to_dms_rational(abs(latitude)),
            piexif.GPSIFD.GPSLongitudeRef: b'E' if longitude >= 0 else b'W',
            piexif.GPSIFD.GPSLongitude: deg_to_dms_rational(abs(longitude)),
        }
        exif_dict['GPS'] = gps_ifd
        exif_bytes = piexif.dump(exif_dict)
        image.save("photo_gps.jpg", exif=exif_bytes)
        st.success("Coordonnées GPS mises à jour et image sauvegardée sous 'photo_gps.jpg'.")

        # Ajout bouton téléchargement PNG
        buffer_gps = BytesIO()
        image.save(buffer_gps, format="PNG")
        buffer_gps.seek(0)
        st.download_button(
            label="📥 Télécharger l'image avec GPS en PNG",
            data=buffer_gps,
            file_name="photo_gps.png",
            mime="image/png"
        )

    # --------- 3. AFFICHER LES COORDONNÉES GPS SUR UNE CARTE ---------
    st.header("3. Afficher la position GPS de la photo sur une carte")
    gps_info = exif_data.get("GPSInfo")
    if gps_info:
        try:
            lat_ref = gps_info[1].decode() if isinstance(gps_info[1], bytes) else gps_info[1]
            lat_dms = gps_info[2]
            lon_ref = gps_info[3].decode() if isinstance(gps_info[3], bytes) else gps_info[3]
            lon_dms = gps_info[4]
            lat_img = dms_rational_to_deg(lat_dms, lat_ref)
            lon_img = dms_rational_to_deg(lon_dms, lon_ref)
            st.map(pd.DataFrame({'lat': [lat_img], 'lon': [lon_img]}))
        except Exception:
            st.warning("Impossible de lire les coordonnées GPS de l'image.")
    else:
        st.info("Aucune coordonnée GPS lue dans l'image. (Ajoutez-les ci-dessus si besoin)")

        # --------- 4. AFFICHAGE DES POI (VOYAGES/RÊVES) ---------
    st.header("4. Carte de vos voyages ou destinations de rêve")
    st.write("Saisissez les lieux (nom, latitude, longitude) à afficher sur la carte. Ajoutez au moins deux points pour voir une ligne.")

    # POI mis à jour avec Paris, Kinshasa, Luxembourg, Bruxelles, Karlsruhe, Dortmund
    default_poi = [
        {"nom": "Paris", "latitude": 48.8566, "longitude": 2.3522},
        {"nom": "Kinshasa", "latitude": -4.4419, "longitude": 15.2663},
        {"nom": "Luxembourg", "latitude": 49.6117, "longitude": 6.1319},
        {"nom": "Bruxelles", "latitude": 50.8503, "longitude": 4.3517},
        {"nom": "Karlsruhe", "latitude": 49.0069, "longitude": 8.4037},
        {"nom": "Dortmund", "latitude": 51.5136, "longitude": 7.4653},
    ]

    poi_df = pd.DataFrame(default_poi)

    poi_input = st.experimental_data_editor(poi_df, num_rows="dynamic", key="poi_editor")

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
