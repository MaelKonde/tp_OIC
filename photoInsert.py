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
import pandas as pd
from io import BytesIO

# --------- FONCTIONS UTILES ---------

def get_exif_data(img):
    exif_data = {}
    if "exif" in img.info:
        exif_dict = piexif.load(img.info["exif"])
        for ifd in exif_dict:
            if not isinstance(exif_dict[ifd], dict): continue
            for tag in exif_dict[ifd]:
                try:
                    tag_name = piexif.TAGS[ifd][tag]["name"]
                    exif_data[tag_name] = exif_dict[ifd][tag]
                except KeyError:
                    pass
    return exif_data

def deg_to_dms_rational(deg_float):
    d = int(deg_float)
    m_f = abs(deg_float - d) * 60
    m = int(m_f)
    s = int((m_f - m) * 60 * 100)
    return ((d,1),(m,1),(s,100))

def dms_rational_to_deg(dms, ref):
    d = dms[0][0]/dms[0][1]
    m = dms[1][0]/dms[1][1]
    s = dms[2][0]/dms[2][1]/100
    val = d + m/60 + s/3600
    return -val if ref in ["S","W"] else val

def get_location_ipapi():
    try:
        resp = requests.get("https://ipapi.co/json/")
        if resp.status_code==200:
            data = resp.json()
            return data.get("latitude"), data.get("longitude")
    except:
        pass
    return 48.949905258671954, 2.886621055934544  # ta position par défaut

def save_image_with_exif(img, exif_dict):
    buf = BytesIO()
    exif_bytes = piexif.dump(exif_dict)
    img.save(buf, format="JPEG", exif=exif_bytes)
    buf.seek(0)
    return buf

def auto_zoom(lat):
    if abs(lat)>50: return 4
    if abs(lat)>20: return 6
    return 8

# --------- APPLICATION ---------

st.set_page_config(page_title="EXIF GPS & POI", layout="wide")
st.title("📸 EXIF GPS + POI")

uploaded = st.file_uploader("Chargez une photo JPEG", type=["jpg","jpeg"])
if not uploaded:
    st.info("Veuillez charger une image JPEG pour démarrer.")
    st.stop()

img = Image.open(uploaded)
st.image(img, use_column_width=True)

lat_current, lon_current = get_location_ipapi()
st.info(f"📍 Position actuelle estimée : {lat_current:.6f}, {lon_current:.6f}")

exif = get_exif_data(img)
gps = exif.get("GPSInfo")
lat_img = lon_img = None
if gps:
    try:
        lat_img = dms_rational_to_deg(gps[2], gps[1].decode() if isinstance(gps[1],bytes) else gps[1])
        lon_img = dms_rational_to_deg(gps[4], gps[3].decode() if isinstance(gps[3],bytes) else gps[3])
    except: pass

st.subheader("📍 Coordonnées GPS dans l’image")
if lat_img and lon_img:
    st.write(f"{lat_img:.6f}, {lon_img:.6f}")
else:
    st.write("Aucune coordonnée GPS trouvée.")

# Saisie
st.subheader("✏️ Saisie/Modification des coordonnées")
lat_def = lat_img if lat_img else lat_current
lon_def = lon_img if lon_img else lon_current

# Init session_state
for key, default in [("lat",lat_def),("lon",lon_def),("show_lat",None),("show_lon",None)]:
    if key not in st.session_state:
        st.session_state[key] = default

st.session_state.lat = st.number_input("Latitude", value=float(st.session_state.lat), format="%.6f")
st.session_state.lon = st.number_input("Longitude", value=float(st.session_state.lon), format="%.6f")

# Comparaison
if abs(st.session_state.lat-lat_current)<0.001 and abs(st.session_state.lon-lon_current)<0.001:
    st.success("✅ Coordonnées correspondent à ta position actuelle.")
else:
    st.error("❌ Coordonnées ne correspondent pas à ta position actuelle.")

# Bouton de mise à jour et stockage
if st.button("Mettre à jour les coordonnées GPS"):
    exif_dict = piexif.load(img.info["exif"]) if "exif" in img.info else {"0th":{}, "Exif":{}, "GPS":{}, "1st":{}, "thumbnail":None}
    gps_ifd = {
        piexif.GPSIFD.GPSLatitudeRef: b"N" if st.session_state.lat>=0 else b"S",
        piexif.GPSIFD.GPSLatitude: deg_to_dms_rational(abs(st.session_state.lat)),
        piexif.GPSIFD.GPSLongitudeRef: b"E" if st.session_state.lon>=0 else b"W",
        piexif.GPSIFD.GPSLongitude: deg_to_dms_rational(abs(st.session_state.lon)),
    }
    exif_dict["GPS"] = gps_ifd
    buf = save_image_with_exif(img, exif_dict)
    st.session_state.modified_image = buf
    st.session_state.show_lat = st.session_state.lat
    st.session_state.show_lon = st.session_state.lon
    st.success("✅ Image modifiée avec nouvelles coordonnées GPS")
    st.download_button("📥 Télécharger image GPS", data=buf, file_name="img_gps.jpg", mime="image/jpeg")

# Affichage carte GPS
if st.session_state.show_lat and st.session_state.show_lon:
    zoom = auto_zoom(st.session_state.show_lat)
    m = folium.Map(location=[st.session_state.show_lat, st.session_state.show_lon], zoom_start=zoom)
    folium.Marker([st.session_state.show_lat, st.session_state.show_lon], popup="Position GPS").add_to(m)
    st.subheader("🗺️ Carte de la position GPS")
    st_folium(m, width=700)

# Section POI
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
if len(poi_input)>=2:
    center = [poi_input.iloc[0]["latitude"], poi_input.iloc[0]["longitude"]]
    voyage_map = folium.Map(location=center, zoom_start=3)
    pts=[]
    for _, r in poi_input.iterrows():
        folium.Marker([r.latitude, r.longitude], popup=r.nom).add_to(voyage_map)
        pts.append((r.latitude,r.longitude))
    folium.PolyLine(pts, color="blue").add_to(voyage_map)
    st.subheader("🗺️ Carte des POI")
    st_folium(voyage_map, width=700)
else:
    st.info("Ajoute au moins deux lieux 😊")
