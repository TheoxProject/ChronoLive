import io

from PIL import Image, ImageDraw, ImageFont


# ============================================================
# POLICES
# ============================================================

def charger_police(
    taille,
    gras=False
):

    if gras:

        chemins = [

            r"C:\Windows\Fonts\arialbd.ttf",

            r"C:\Windows\Fonts\calibrib.ttf"

        ]

    else:

        chemins = [

            r"C:\Windows\Fonts\arial.ttf",

            r"C:\Windows\Fonts\calibri.ttf"

        ]


    for chemin in chemins:

        try:

            return ImageFont.truetype(
                chemin,
                taille
            )

        except OSError:

            continue


    return ImageFont.load_default()


# ============================================================
# OUTILS
# ============================================================

def formater_temps(centisecondes):

    if centisecondes is None:
        return "-"

    heures = centisecondes // 360000

    minutes = (
        centisecondes // 6000
    ) % 60

    secondes = (
        centisecondes // 100
    ) % 60

    centiemes = (
        centisecondes % 100
    )

    return (
        f"{heures:02d}:"
        f"{minutes:02d}:"
        f"{secondes:02d}."
        f"{centiemes:02d}"
    )


def formater_ecart(centisecondes):

    if (
        centisecondes is None
        or centisecondes == 0
    ):
        return "-"

    return (
        "+"
        + formater_temps(
            centisecondes
        )
    )


# ============================================================
# EXPORT PNG
# ============================================================

def exporter_png(
    resultat,
    titre,
    course,
    type_classement
):

    largeur = 1400

    marge = 70

    hauteur_header = 80

    hauteur_titre = 110

    hauteur_entete = 45

    hauteur_ligne = 52

    hauteur_footer = 55


    hauteur = (

        marge

        + hauteur_header

        + hauteur_titre

        + hauteur_entete

        + (
            len(resultat)
            * hauteur_ligne
        )

        + hauteur_footer

        + marge

    )


    image = Image.new(
        "RGB",
        (
            largeur,
            hauteur
        ),
        "#FFFFFF"
    )


    dessin = ImageDraw.Draw(
        image
    )


    # ========================================================
    # POLICES
    # ========================================================

    police_logo = charger_police(
        28,
        True
    )

    police_titre = charger_police(
        36,
        True
    )

    police_info = charger_police(
        18,
        False
    )

    police_entete = charger_police(
        16,
        True
    )

    police_nom = charger_police(
        19,
        True
    )

    police_cellule = charger_police(
        18,
        False
    )

    police_temps = charger_police(
        20,
        True
    )


    # ========================================================
    # COULEURS
    # ========================================================

    VERT = "#5B8E73"

    VERT_PALE = "#EDF4EF"

    VERT_TRES_PALE = "#F7FAF8"

    TEXTE = "#334155"

    GRIS = "#718078"

    BORDURE = "#E4EAE6"


    # ========================================================
    # LOGO
    # ========================================================

    dessin.text(

        (
            marge,
            marge
        ),

        f"{course.nom} · {course.date.strftime('%d/%m/%Y')}",

        font=police_logo,

        fill=VERT

    )


    dessin.text(

        (
            largeur - marge,
            marge + 8
        ),

        "RÉSULTATS",

        font=police_info,

        fill=GRIS,

        anchor="ra"

    )


    # ========================================================
    # LIGNE HEADER
    # ========================================================

    y_ligne = (
        marge
        + hauteur_header
        - 10
    )


    dessin.line(

        (
            marge,
            y_ligne,
            largeur - marge,
            y_ligne
        ),

        fill=BORDURE,

        width=2
    )


    # ========================================================
    # TITRE
    # ========================================================

    y_titre = (
        y_ligne
        + 28
    )


    dessin.text(

        (
            marge,
            y_titre
        ),

        titre,

        font=police_titre,

        fill=TEXTE

    )


    # ========================================================
    # INFOS
    # ========================================================

    texte_info = (

        f"{len(resultat)} "

        + (
            "coureur classé"
            if len(resultat) == 1
            else "coureurs classés"
        )

    )


    dessin.text(

        (
            marge,
            y_titre + 52
        ),

        texte_info,

        font=police_info,

        fill=GRIS

    )


    # ========================================================
    # TABLEAU
    # ========================================================

    y = (
        y_titre
        + hauteur_titre
        - 15
    )


    # --------------------------------------------------------
    # POSITIONS DES COLONNES
    # --------------------------------------------------------

    x_pos = marge

    x_dossard = 170

    x_coureur = 310

    x_sexe = 760

    x_categorie = 880

    x_temps = 1120

    x_ecart = 1280


    # ========================================================
    # EN-TETE
    # ========================================================

    dessin.rectangle(

        (
            marge,
            y,
            largeur - marge,
            y + hauteur_entete
        ),

        fill=VERT_PALE

    )


    entetes = [

        (
            "POS.",
            x_pos
        ),

        (
            "DOSSARD",
            x_dossard
        ),

        (
            "COUREUR",
            x_coureur
        ),

        (
            "SEXE",
            x_sexe
        ),

        (
            "CATÉGORIE",
            x_categorie
        ),

        (
            "TEMPS",
            x_temps
        ),

        (
            "ÉCART",
            x_ecart
        )

    ]


    for texte, x in entetes:

        dessin.text(

            (
                x,
                y + 13
            ),

            texte,

            font=police_entete,

            fill=GRIS,

            anchor="ma"

        )


    y += hauteur_entete


    # ========================================================
    # LIGNES
    # ========================================================

    for index, coureur in enumerate(
        resultat
    ):

        if index == 0:

            dessin.rectangle(

                (
                    marge,
                    y,
                    largeur - marge,
                    y + hauteur_ligne
                ),

                fill=VERT_PALE

            )

        elif index % 2 == 1:

            dessin.rectangle(

                (
                    marge,
                    y,
                    largeur - marge,
                    y + hauteur_ligne
                ),

                fill=VERT_TRES_PALE

            )


        # ----------------------------------------------------
        # CATEGORIE
        # ----------------------------------------------------

        if type_classement == "categorie_ffc":

            categorie = (
                coureur.get(
                    "categorie_ffc"
                )
                or "-"
            )

        elif type_classement == "scratch":

            categorie = (
                coureur.get(
                    "categorie"
                )
                or "-"
            )

            categorie_ffc = (
                coureur.get(
                    "categorie_ffc"
                )
                or "-"
            )

            categorie = (
                categorie
                + " / "
                + categorie_ffc
            )

        else:

            categorie = (
                coureur.get(
                    "categorie"
                )
                or "-"
            )


        dossard = (

            f"#{coureur['dossard']}"

            if coureur.get(
                "dossard"
            ) is not None

            else "-"

        )


        nom = (

            coureur.get(
                "nom",
                ""
            )

            + " "

            + coureur.get(
                "prenom",
                ""
            )

        ).strip()


        temps = formater_temps(
            coureur[
                "temps_centisecondes"
            ]
        )


        ecart = formater_ecart(
            coureur[
                "ecart_centisecondes"
            ]
        )


        # ----------------------------------------------------
        # TEXTE
        # ----------------------------------------------------

        dessin.text(

            (
                x_pos + 15,
                y + 14
            ),

            str(
                coureur["position"]
            ),

            font=police_cellule,

            fill=VERT

        )


        dessin.text(

            (
                x_dossard,
                y + 14
            ),

            dossard,

            font=police_cellule,

            fill=TEXTE,

            anchor="ma"

        )


        dessin.text(

            (
                x_coureur,
                y + 14
            ),

            nom,

            font=police_nom,

            fill=TEXTE

        )


        dessin.text(

            (
                x_sexe,
                y + 14
            ),

            coureur.get(
                "sexe",
                "-"
            ),

            font=police_cellule,

            fill=GRIS,

            anchor="ma"

        )


        dessin.text(

            (
                x_categorie,
                y + 14
            ),

            categorie,

            font=police_cellule,

            fill=TEXTE,

            anchor="ma"

        )


        dessin.text(

            (
                x_temps,
                y + 14
            ),

            temps,

            font=police_temps,

            fill=TEXTE,

            anchor="ma"

        )


        dessin.text(

            (
                x_ecart,
                y + 14
            ),

            ecart,

            font=police_cellule,

            fill=GRIS,

            anchor="ma"

        )


        dessin.line(

            (
                marge,
                y + hauteur_ligne,
                largeur - marge,
                y + hauteur_ligne
            ),

            fill=BORDURE,

            width=1

        )


        y += hauteur_ligne


    # ========================================================
    # FOOTER
    # ========================================================

    dessin.text(

        (
            largeur // 2,
            y + 25
        ),

        "ChronoLive · Résultats officiels",

        font=police_info,

        fill=GRIS,

        anchor="ma"

    )


    # ========================================================
    # SORTIE
    # ========================================================

    sortie = io.BytesIO()


    image.save(
        sortie,
        format="PNG"
    )


    sortie.seek(0)

    return sortie.getvalue()

