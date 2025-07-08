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
import requests
from io import BytesIO

# --------- FONCTIONS UTILES ---------

def get_exif_data(img):
    exif_data = {}
    if "exif" in img.info:
        exif_dict = piexif.load(img.info["exif"])
        for ifd in exif_dict:
            if not isinstance(exif_dict[ifd], dict):
                continue
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

def save_image_with_exif(image, exif_dict):
    exif_bytes = piexif.dump(exif_dict)
    buffer = BytesIO()
    image.save(buffer, format="JPEG", exif=exif_bytes)
    buffer.seek(0)
    return buffer

def auto_zoom(lat):
    if abs(lat) > 50:
        return 4
    elif abs(lat) > 20:
        return 6
    else:
        return 8

# --------- STREAMLIT ---------

st.set_page_config(page_title="EXIF GPS & Carte", layout="wide")
st.title("Modifier et valider les coordonnées GPS EXIF")

uploaded_file = st.file_uploader("Chargez une photo (JPEG uniquement)", type=["jpg", "jpeg"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Photo chargée", use_column_width=True)

    lat_current, lon_current = get_location_ipapi()
    if lat_current and lon_current:
        st.info(f"Position actuelle détectée : Latitude {lat_current:.6f}, Longitude {lon_current:.6f}")
    else:
        st.warning("Impossible de détecter la position actuelle automatiquement.")

    exif_data = get_exif_data(image)
    gps_info = exif_data.get("GPSInfo", None)

    lat_img, lon_img = None, None
    if gps_info:
        try:
            lat_ref = gps_info[1].decode() if isinstance(gps_info[1], bytes) else gps_info[1]
            lat_dms = gps_info[2]
            lon_ref = gps_info[3].decode() if isinstance(gps_info[3], bytes) else gps_info[3]
            lon_dms = gps_info[4]
            lat_img = dms_rational_to_deg(lat_dms, lat_ref)
            lon_img = dms_rational_to_deg(lon_dms, lon_ref)
        except Exception:
            pass

    st.subheader("Coordonnées GPS actuelles dans l'image")
    if lat_img and lon_img:
        st.write(f"Latitude : {lat_img:.6f}, Longitude : {lon_img:.6f}")
    else:
        st.write("Aucune coordonnée GPS trouvée dans l'image.")

    st.subheader("Saisissez ou modifiez les coordonnées GPS")

    lat_default = lat_img if lat_img else (lat_current if lat_current else 0.0)
    lon_default = lon_img if lon_img else (lon_current if lon_current else 0.0)

    # Utiliser session_state pour mémoriser saisie (si déjà initialisé)
    if "latitude" not in st.session_state:
        st.session_state.latitude = lat_default
    if "longitude" not in st.session_state:
        st.session_state.longitude = lon_default
    if "show_lat" not in st.session_state:
        st.session_state.show_lat = lat_default
    if "show_lon" not in st.session_state:
        st.session_state.show_lon = lon_default

    # Inputs modifient session_state
    st.session_state.latitude = st.number_input("Latitude", value=st.session_state.latitude, format="%.6f", key="lat_input")
    st.session_state.longitude = st.number_input("Longitude", value=st.session_state.longitude, format="%.6f", key="lon_input")

    # Message vert ou rouge selon correspondance
    if lat_current and lon_current:
        diff_lat = abs(st.session_state.latitude - lat_current)
        diff_lon = abs(st.session_state.longitude - lon_current)
        if diff_lat < 0.001 and diff_lon < 0.001:
            st.success("✔️ Les coordonnées correspondent à votre position actuelle.")
        else:
            st.error("❌ Les coordonnées ne correspondent pas à votre position actuelle.")
    else:
        st.info("Position actuelle non disponible pour validation.")

    # Bouton pour enregistrer coordonnées et image modifiée
    if st.button("Mettre à jour les coordonnées GPS dans l'image"):
        exif_dict = piexif.load(image.info["exif"]) if "exif" in image.info else {"0th":{}, "Exif":{}, "GPS":{}, "1st":{}, "thumbnail": None}
        gps_ifd = {
            piexif.GPSIFD.GPSLatitudeRef: b'N' if st.session_state.latitude >= 0 else b'S',
            piexif.GPSIFD.GPSLatitude: deg_to_dms_rational(abs(st.session_state.latitude)),
            piexif.GPSIFD.GPSLongitudeRef: b'E' if st.session_state.longitude >= 0 else b'W',
            piexif.GPSIFD.GPSLongitude: deg_to_dms_rational(abs(st.session_state.longitude)),
        }
        exif_dict['GPS'] = gps_ifd
        buffer = save_image_with_exif(image, exif_dict)
        st.session_state.modified_image = buffer  # Stocker l'image modifiée en session_state

        # Mettre à jour la position à afficher sur la carte
        st.session_state.show_lat = st.session_state.latitude
        st.session_state.show_lon = st.session_state.longitude

        st.success("Coordonnées GPS mises à jour dans l'image.")
        st.download_button(
            label="📥 Télécharger l'image modifiée avec GPS",
            data=st.session_state.modified_image,
            file_name="photo_gps_modifiee.jpg",
            mime="image/jpeg"
        )

    # Affichage carte tout le temps si coords valides
    if st.session_state.show_lat is not None and st.session_state.show_lon is not None:
        zoom = auto_zoom(st.session_state.show_lat)
        m = folium.Map(location=[st.session_state.show_lat, st.session_state.show_lon], zoom_start=zoom)
        folium.Marker([st.session_state.show_lat, st.session_state.show_lon], popup="Position GPS").add_to(m)
        st.subheader("Carte centrée sur les coordonnées sélectionnées")
        st_folium(m, width=700)

else:
    st.info("Chargez une photo JPEG pour commencer.")

# --------- Affichage des POI (voyages/rêves) ---------
    st.header("4. Carte de vos voyages ou destinations de rêve")
    st.write("Saisissez les lieux (nom, latitude, longitude) à afficher sur la carte. Ajoutez au moins deux points pour voir une ligne.")

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
        m = folium.Map(location=[poi_input.iloc[0]["latitude"], poi_input.iloc[0]["longitude"]], zoom_start=2)
        points = []
        for idx, row in poi_input.iterrows():
            folium.Marker([row["latitude"], row["longitude"]], popup=row["nom"]).add_to(m)
            points.append((row["latitude"], row["longitude"]))
        folium.PolyLine(points, color="blue", weight=2.5, opacity=1).add_to(m)
        st_folium(m, width=700)
    else:
        st.info("Ajoutez au moins deux destinations pour afficher la carte.")
