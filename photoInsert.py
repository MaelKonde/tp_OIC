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
from PIL.ExifTags import TAGS
import piexif

# Widget Streamlit pour charger une image (jpg, jpeg, png)
uploaded_file = st.file_uploader("Chargez une photo", type=["jpg", "jpeg", "png"])
if uploaded_file:
    # Ouvre l'image avec Pillow
    image = Image.open(uploaded_file)
    # Affiche l'image dans l'application Streamlit avec une légende
    st.image(image, caption="Votre photo", use_column_width=True)

def get_exif_data(img):
    """
    Extrait les métadonnées EXIF d'une image PIL et les retourne sous forme de dictionnaire lisible.
    """
    exif_data = {}
    info = img._getexif()  # Récupère les données EXIF brutes (fonctionne surtout pour JPEG)
    if info:
        for tag, value in info.items():
            decoded = TAGS.get(tag, tag)  # Traduit l'ID du tag en nom lisible
            exif_data[decoded] = value
    return exif_data

if uploaded_file:
    # Extraction et affichage des métadonnées EXIF existantes
    exif_data = get_exif_data(image)
    st.write("Métadonnées EXIF existantes :", exif_data)

if uploaded_file:
    artist_default = exif_data.get('Artist', '') if 'exif_data' in locals() else ''
    artist = st.text_input("Auteur/Artiste", value=artist_default)

    if st.button("Mettre à jour les EXIF"):
        try:
            # Vérifier si l'image a déjà des EXIF
            if "exif" in image.info:
                exif_dict = piexif.load(image.info["exif"])
            else:
                # Créer un dictionnaire EXIF vide si pas d'EXIF existant (pour JPEG)
                exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

            # Met à jour le champ 'Artist' dans le bloc 0th (informations principales)
            exif_dict['0th'][piexif.ImageIFD.Artist] = artist.encode('utf-8')
            # Sérialise les EXIF modifiées
            exif_bytes = piexif.dump(exif_dict)

            # Sauvegarde l'image modifiée localement avec les nouveaux EXIF
            # Important : ne fonctionne qu'avec JPEG (pas PNG)
            if image.format == "JPEG":
                image.save("output.jpg", exif=exif_bytes)
                st.success("EXIF mis à jour et image sauvegardée sous output.jpg")
            else:
                st.error("La mise à jour des EXIF ne fonctionne que sur les images JPEG.")
        except Exception as e:
            st.error(f"Erreur lors de la mise à jour des EXIF : {e}")
