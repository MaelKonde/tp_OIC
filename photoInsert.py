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
from datetime import datetime

# === Fonctions utilitaires ===

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

# === Interface ===

st.title("🖼️ EXIF & GPS avancé + POI")

uploaded = st.file_uploader("📤 Importer une image JPEG", type=["jpg","jpeg"])
if not uploaded:
    st.stop()

img = Image.open(uploaded)
st.image(img, use_column_width=True)

# Lecture EXIF existant
exif = piexif.load(img.info.get("exif", b""))
lat_img, lon_img = extract_gps_data(exif)

# Affichage EXIF brut en JSON
st.subheader("🔍 Métadonnées EXIF actuelles")
st.json({k: {piexif.TAGS[k][tag]["name"]: str(val) for tag,val in v.items() if tag in piexif.TAGS[k]} for k,v in exif.items() if isinstance(v, dict)})

# Formulaire EXIF professionnel (ajout d'options avancées)
st.subheader("🛠️ Formulaire EXIF professionnel")
make = st.text_input("Make", exif["0th"].get(piexif.ImageIFD.Make,b"").decode(errors="ignore"))
model = st.text_input("Model", exif["0th"].get(piexif.ImageIFD.Model,b"").decode(errors="ignore"))
artist = st.text_input("Artist", exif["0th"].get(piexif.ImageIFD.Artist,b"").decode(errors="ignore"))
copyright = st.text_input("Copyright", exif["0th"].get(piexif.ImageIFD.Copyright,b"").decode(errors="ignore"))
software = st.text_input("Software", exif["0th"].get(piexif.ImageIFD.Software,b"").decode(errors="ignore"))
desc = st.text_input("Description", exif["0th"].get(piexif.ImageIFD.ImageDescription,b"").decode(errors="ignore"))
dto = st.text_input("DateTimeOriginal", exif["Exif"].get(piexif.ExifIFD.DateTimeOriginal,b"").decode(errors="ignore"))
# Options professionnelles ajoutées :
job_name = st.text_input("Job Name", exif["0th"].get(40091, b"").decode(errors="ignore"))  # Tag non standard, exemple
client = st.text_input("Client", exif["0th"].get(40092, b"").decode(errors="ignore"))      # Tag non standard, exemple
location = st.text_input("Lieu de prise de vue", exif["0th"].get(40093, b"").decode(errors="ignore")) # Tag non standard, exemple
contact = st.text_input("Contact Photographe", exif["0th"].get(40094, b"").decode(errors="ignore"))   # Tag non standard, exemple

# Saisie et validation coordonnées GPS (modifiable)
lat_input = st.number_input("📍 Nouvelle latitude", value=lat_img if lat_img is not None else 48.9601, format="%.6f")
lon_input = st.number_input("📍 Nouvelle longitude", value=lon_img if lon_img is not None else 2.8787, format="%.6f")

# Saisie de coordonnées GPS pour vérification
st.markdown("**Validation de coordonnées GPS externes**")
lat_check = st.number_input("Latitude à vérifier", value=lat_input, format="%.6f", key="lat_check")
lon_check = st.number_input("Longitude à vérifier", value=lon_input, format="%.6f", key="lon_check")
if st.button("Valider la correspondance avec l'image"):
    match = (abs(lat_check - lat_img) < 0.0001 and abs(lon_check - lon_img) < 0.0001)
    st.info("✅ Correspondance parfaite." if match else "❌ Les coordonnées ne correspondent pas à l'image.")

# Bouton unique pour tout enregistrer et télécharger
if st.button("💾 Enregistrer EXIF & GPS puis télécharger l’image"):
    # Mise à jour EXIF
    exif["0th"][piexif.ImageIFD.Make] = make.encode()
    exif["0th"][piexif.ImageIFD.Model] = model.encode()
    exif["0th"][piexif.ImageIFD.Artist] = artist.encode()
    exif["0th"][piexif.ImageIFD.Copyright] = copyright.encode()
    exif["0th"][piexif.ImageIFD.Software] = software.encode()
    exif["0th"][piexif.ImageIFD.ImageDescription] = desc.encode()
    exif["Exif"][piexif.ExifIFD.DateTimeOriginal] = dto.encode()
    # Champs professionnels (utilise des tags personnalisés ou IPTC/XMP dans une vraie appli)
    exif["0th"][40091] = job_name.encode()
    exif["0th"][40092] = client.encode()
    exif["0th"][40093] = location.encode()
    exif["0th"][40094] = contact.encode()
    # Mise à jour GPS
    gps_ifd = {
        piexif.GPSIFD.GPSLatitudeRef: b"N" if lat_input>=0 else b"S",
        piexif.GPSIFD.GPSLatitude: deg_to_dms_rational(abs(lat_input)),
        piexif.GPSIFD.GPSLongitudeRef: b"E" if lon_input>=0 else b"W",
        piexif.GPSIFD.GPSLongitude: deg_to_dms_rational(abs(lon_input)),
    }
    exif["GPS"] = gps_ifd

    buf = save_with_exif(img, exif)
    st.success("✅ Image prête au téléchargement.")

    # Affichage carte avec coordonnées choisies et Meaux
    m = folium.Map(location=[lat_input, lon_input], zoom_start=zoom_for(lat_input))
    folium.Marker([lat_input, lon_input], popup="Coordonnées enregistrées", icon=folium.Icon(color="blue")).add_to(m)
    folium.Marker([48.9601, 2.8787], popup="Position de Meaux", icon=folium.Icon(color="green")).add_to(m)
    st.subheader("🗺️ Résultat GPS")
    st_folium(m, width=700)

    # Téléchargement
    st.download_button("📥 Télécharger l’image modifiée", data=buf, file_name="image_modifiee.jpg", mime="image/jpeg")

# Section POI
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
