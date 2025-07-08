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
from datetime import datetime

# === fonctions utilitaires ===

def deg_to_dms_rational(deg_float):
    m_float = (deg_float - int(deg_float)) * 60
    s_float = (m_float - int(m_float)) * 60
    return [(int(deg_float),1),(int(m_float),1),(int(s_float*100),100)]

def dms_to_deg(value):
    d, m, s = value
    return d[0]/d[1] + m[0]/m[1]/60 + s[0]/s[1]/3600

def extract_gps_data(exif):
    gps = exif.get("GPS", {})
    if gps:
        lat = dms_to_deg(gps.get(piexif.GPSIFD.GPSLatitude, [(0,1),(0,1),(0,1)]))
        lon = dms_to_deg(gps.get(piexif.GPSIFD.GPSLongitude, [(0,1),(0,1),(0,1)]))
        ref_lat = gps.get(piexif.GPSIFD.GPSLatitudeRef, b"N").decode()
        ref_lon = gps.get(piexif.GPSIFD.GPSLongitudeRef, b"E").decode()
        if ref_lat == "S": lat = -lat
        if ref_lon == "W": lon = -lon
        return lat, lon
    return None, None

def save_with_exif(img, exif_dict):
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=piexif.dump(exif_dict))
    buf.seek(0)
    return buf

def zoom_for(lat):
    return 4 if abs(lat)>60 else 6 if abs(lat)>30 else 10

# === interface ===

st.title("🖼️ EXIF & GPS avancé + POI")

uploaded = st.file_uploader("📤 Importer une image JPEG", type=["jpg","jpeg"])
if not uploaded:
    st.stop()

img = Image.open(uploaded)
st.image(img, use_column_width=True)

# lecture EXIF existant
exif = piexif.load(img.info.get("exif", b""), )

lat_img, lon_img = extract_gps_data(exif)

# affichage EXIF brut en JSON
st.subheader("🔍 Métadonnées EXIF actuelles")
st.json({k: {piexif.TAGS[k][tag]["name"]: str(val) for tag,val in v.items() if tag in piexif.TAGS[k]} for k,v in exif.items() if isinstance(v, dict)})

# formulaire EXIF professionnel
st.subheader("🛠️ Formulaire EXIF professionnel")
make = st.text_input("Make", exif["0th"].get(piexif.ImageIFD.Make,b"").decode(errors="ignore"))
model = st.text_input("Model", exif["0th"].get(piexif.ImageIFD.Model,b"").decode(errors="ignore"))
artist = st.text_input("Artist", exif["0th"].get(piexif.ImageIFD.Artist,b"").decode(errors="ignore"))
copyright = st.text_input("Copyright", exif["0th"].get(piexif.ImageIFD.Copyright,b"").decode(errors="ignore"))
software = st.text_input("Software", exif["0th"].get(piexif.ImageIFD.Software,b"").decode(errors="ignore"))
desc = st.text_input("Description", exif["0th"].get(piexif.ImageIFD.ImageDescription,b"").decode(errors="ignore"))
dto = st.text_input("DateTimeOriginal", exif["Exif"].get(piexif.ExifIFD.DateTimeOriginal,b"").decode(errors="ignore"))

# boutons validant GPS & EXIF
lat_input = st.number_input("📍 Nouvelle latitude", value=lat_img if lat_img is not None else 48.9601, format="%.6f")
lon_input = st.number_input("📍 Nouvelle longitude", value=lon_img if lon_img is not None else 2.8787, format="%.6f")

if st.button("💾 Enregistrer et télécharger l’image"):
    # mise à jour EXIF
    exif["0th"][piexif.ImageIFD.Make] = make.encode()
    exif["0th"][piexif.ImageIFD.Model] = model.encode()
    exif["0th"][piexif.ImageIFD.Artist] = artist.encode()
    exif["0th"][piexif.ImageIFD.Copyright] = copyright.encode()
    exif["0th"][piexif.ImageIFD.Software] = software.encode()
    exif["0th"][piexif.ImageIFD.ImageDescription] = desc.encode()
    exif["Exif"][piexif.ExifIFD.DateTimeOriginal] = dto.encode()

    # mise à jour GPS
    gps_ifd = {
        piexif.GPSIFD.GPSLatitudeRef: b"N" if lat_input>=0 else b"S",
        piexif.GPSIFD.GPSLatitude: deg_to_dms_rational(abs(lat_input)),
        piexif.GPSIFD.GPSLongitudeRef: b"E" if lon_input>=0 else b"W",
        piexif.GPSIFD.GPSLongitude: deg_to_dms_rational(abs(lon_input)),
    }
    exif["GPS"] = gps_ifd

    buf = save_with_exif(img, exif)
    st.success("✅ Image prête au téléchargement.")

    # validation coordonnées
    match = (abs(lat_input-48.9601)<0.001 and abs(lon_input-2.8787)<0.001)
    st.info("✅ Coordonnées valides." if match else "⚠️ Coordonnées différentes de la position actuelle.")

    # affichage des points sur carte
    m = folium.Map(location=[48.9601,2.8787], zoom_start=8)
    folium.Marker([48.9601,2.8787], popup="Position actuelle (Meaux)", icon=folium.Icon(color="green")).add_to(m)
    folium.Marker([lat_input,lon_input], popup="Coordonnées enregistrées", icon=folium.Icon(color="blue")).add_to(m)
    st.subheader("🗺️ Résultat GPS")
    st_folium(m, width=700)

    # téléchargement
    st.download_button("📥 Télécharger l’image modifiée", data=buf, file_name="image_modifiee.jpg", mime="image/jpeg")

# section POI
st.header("4. POI – Destinations de rêve")
default = [{"nom":"Paris","latitude":48.8566,"longitude":2.3522},
           {"nom":"Kinshasa","latitude":-4.4419,"longitude":15.2663},
           {"nom":"Luxembourg","latitude":49.6117,"longitude":6.1319},
           {"nom":"Bruxelles","latitude":50.8503,"longitude":4.3517},
           {"nom":"Karlsruhe","latitude":49.0069,"longitude":8.4037},
           {"nom":"Dortmund","latitude":51.5136,"longitude":7.4653}]
poi_df = pd.DataFrame(default)
poi_input = st.data_editor(poi_df, num_rows="dynamic", key="poi")
if len(poi_input)>=2:
    vm = folium.Map(location=[poi_input.iloc[0].latitude, poi_input.iloc[0].longitude], zoom_start=3)
    pts=[]
    for _,r in poi_input.iterrows():
        folium.Marker([r.latitude,r.longitude], popup=r.nom).add_to(vm)
        pts.append((r.latitude,r.longitude))
    folium.PolyLine(pts, color="blue").add_to(vm)
    st.subheader("🗺️ Carte des POI")
    st_folium(vm, width=700)
else:
    st.info("Ajoute au moins deux POI pour voir la carte 😊")
