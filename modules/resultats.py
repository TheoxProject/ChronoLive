#-----------
# MODULE 4 - RÉSULTATS
#-----------
# Gestion de l'affichage et de l'export des résultats
# de la course.
#
# Fonctionnalités :
# - classement scratch
# - classement par catégorie
# - classement par catégorie FFC
# - classement par sexe
# - export PDF, PNG, Excel et CSV
#
# Une base SQLite correspond à UNE seule course.
#
# Routes :
# - /resultats
# - /export_resultats
#-----------

import re
from io import BytesIO
from zipfile import ZipFile

from flask import (
    Blueprint,
    render_template,
    request,
    send_file,
)

from config import CATEGORIES, CATEGORIES_FFC
from database import Session
from models import Course, Coureur
from utils.temps import formater_temps

from exports.pdf import exporter_pdf
from exports.png import exporter_png
from exports.excel import exporter_excel
from exports.csv import exporter_csv


resultats_bp = Blueprint(
    "resultats",
    __name__
)


SEXES = {
    "M": "Hommes",
    "F": "Femmes",
}


def construire_resultat(
    session,
    type_classement="scratch",
    valeur=None
):
    # Construit le classement demandé.

    coureurs = (
        session.query(Coureur)
        .filter(
            Coureur.temps_centisecondes.isnot(None)
        )
    )

    # Application du filtre sélectionné.
    if type_classement == "categorie" and valeur:
        coureurs = coureurs.filter(
            Coureur.categorie == valeur
        )

    elif type_classement == "categorie_ffc" and valeur:
        coureurs = coureurs.filter(
            Coureur.categorie_ffc == valeur
        )

    elif type_classement == "sexe" and valeur:
        coureurs = coureurs.filter(
            Coureur.sexe == valeur
        )

    # Classement du plus rapide au plus lent.
    coureurs = (
        coureurs
        .order_by(
            Coureur.temps_centisecondes.asc()
        )
        .all()
    )

    if not coureurs:
        return []

    # Le premier coureur sert de référence pour les écarts.
    meilleur_temps = (
        coureurs[0].temps_centisecondes
    )

    resultats = []

    for position, coureur in enumerate(
        coureurs,
        start=1
    ):
        resultats.append({
            "position": position,
            "dossard": coureur.dossard,
            "nom": coureur.nom,
            "prenom": coureur.prenom,
            "club": coureur.club,
            "categorie": coureur.categorie,
            "categorie_ffc": (
                coureur.categorie_ffc or "-"
            ),
            "sexe": coureur.sexe,
            "heure_depart": coureur.heure_depart,
            "heure_arrivee": coureur.heure_arrivee,
            "temps_centisecondes": (
                coureur.temps_centisecondes
            ),
            "ecart_centisecondes": (
                coureur.temps_centisecondes
                - meilleur_temps
            ),
        })

    return resultats


@resultats_bp.route("/resultats")
def page_resultats():
    # Affiche la page de consultation des résultats.

    type_classement = request.args.get(
        "type",
        "scratch"
    )

    valeur = request.args.get(
        "valeur"
    )

    session = Session()

    try:
        course = (
            session.query(Course)
            .first()
        )

        resultats_data = construire_resultat(
            session,
            type_classement,
            valeur
        )

        # Détermine le titre affiché sur la page.
        titres = {
            "scratch": "Classement Scratch",

            "categorie": (
                f"Classement {valeur}"
                if valeur
                else "Classement par catégorie"
            ),

            "categorie_ffc": (
                f"Classement FFC {valeur}"
                if valeur
                else "Classement par catégorie FFC"
            ),

            "sexe": (
                f"Classement {valeur}"
                if valeur
                else "Classement par sexe"
            ),
        }

        titre = titres.get(
            type_classement,
            "Résultats"
        )

        resultats_apercu = resultats_data[:5] #Affiche seulement les 5 premiers

        return render_template(
            "resultats.html",
            resultats=resultats_apercu,
            titre=titre,
            categories=CATEGORIES,
            categories_ffc=CATEGORIES_FFC,
            course_nom=course.nom,
            course_lieu=course.lieu,
            course_date=course.date,
            type_classement=type_classement,
            valeur=valeur,
            formater_temps=formater_temps,
        )

    finally:
        session.close()


@resultats_bp.route("/export_resultats")
def export_resultats():
    # Génère et télécharge les résultats dans le format demandé.

    type_classement = request.args.get(
        "type",
        "scratch"
    )

    valeur = request.args.get(
        "valeur"
    )

    format_export = request.args.get(
        "format",
        "pdf"
    )

    formats_autorises = {
        "pdf",
        "png",
        "excel",
        "csv",
    }

    types_autorises = {
        "scratch",
        "categorie",
        "categorie_ffc",
        "sexe",
    }

    if format_export not in formats_autorises:
        return "Format d'export invalide.", 400

    if type_classement not in types_autorises:
        return "Type de classement invalide.", 400

    session = Session()

    try:
        course = (
            session.query(Course)
            .first()
        )

        # Cas particulier :
        # export de toutes les catégories dans un ZIP.
        if (
            type_classement in {
                "categorie",
                "categorie_ffc",
            }
            and not valeur
        ):
            categories_export = (
                CATEGORIES
                if type_classement == "categorie"
                else CATEGORIES_FFC
            )

            zip_buffer = BytesIO()

            with ZipFile(
                zip_buffer,
                "w"
            ) as zip_file:

                for categorie in categories_export:

                    resultats_data = construire_resultat(
                        session,
                        type_classement,
                        categorie
                    )

                    # Ignore les catégories sans coureur classé.
                    if not resultats_data:
                        continue

                    titre = (
                        f"Classement {categorie}"
                        if type_classement == "categorie"
                        else f"Classement FFC {categorie}"
                    )

                    categorie_export = categorie

                    fichier = generer_export(
                        format_export,
                        resultats_data,
                        course,
                        titre,
                        categorie_export,
                    )

                    nom_categorie = re.sub(
                        r'[\\/*?:"<>|]',
                        "_",
                        categorie
                    )

                    extension = {
                        "pdf": "pdf",
                        "png": "png",
                        "excel": "xlsx",
                        "csv": "csv",
                    }[format_export]

                    nom_fichier = (
                        f"{nom_categorie}.{extension}"
                    )

                    zip_file.writestr(
                        nom_fichier,
                        fichier
                    )

            zip_buffer.seek(0)

            nom_zip = (
                "resultats_categories.zip"
                if type_classement == "categorie"
                else "resultats_categories_ffc.zip"
            )

            return send_file(
                zip_buffer,
                mimetype="application/zip",
                as_attachment=True,
                download_name=nom_zip,
            )

        # Construction du classement demandé.
        resultats_data = construire_resultat(
            session,
            type_classement,
            valeur
        )

        if type_classement == "scratch":
            titre = "Classement Scratch"

        elif type_classement == "categorie":
            titre = f"Classement {valeur}"
            categorie_export = valeur

        elif type_classement == "categorie_ffc":
            titre = f"Classement FFC {valeur}"
            categorie_export = valeur

        elif type_classement == "sexe":
            titre = SEXES.get(
                valeur,
                valeur
            )

        fichier = generer_export(
            format_export,
            resultats_data,
            course,
            titre,
            locals().get("categorie_export"),
        )

        extensions = {
            "pdf": "pdf",
            "png": "png",
            "excel": "xlsx",
            "csv": "csv",
        }

        mimetypes = {
            "pdf": "application/pdf",
            "png": "image/png",
            "excel": (
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            "csv": "text/csv",
        }

        extension = extensions[format_export]

        nom_fichier = (
            f"resultats_{type_classement}"
        )

        if valeur:
            nom_valeur = re.sub(
                r'[\\/*?:"<>|]',
                "_",
                valeur
            )

            nom_fichier += f"_{nom_valeur}"

        nom_fichier += f".{extension}"

        return send_file(
            BytesIO(fichier),
            mimetype=mimetypes[format_export],
            as_attachment=True,
            download_name=nom_fichier,
        )

    finally:
        session.close()


def generer_export(
    format_export,
    resultats_data,
    course,
    titre,
    categorie_export=None,
):
    # Sélectionne le générateur correspondant au format demandé.

    if format_export == "pdf":
        return exporter_pdf(
            resultats_data,
            titre,
            course,
        )

    if format_export == "png":
        return exporter_png(
            resultats_data,
            titre,
            course,
            categorie_export,
        )

    if format_export == "excel":
        return exporter_excel(
            resultats_data,
            titre,
            categorie_export,
        )

    if format_export == "csv":
        return exporter_csv(
            resultats_data,
            categorie_export,
        )

    raise ValueError(
        "Format d'export inconnu."
    )