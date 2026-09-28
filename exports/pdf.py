import io

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)


# ============================================================
# POLICES
# ============================================================

try:

    pdfmetrics.registerFont(
        TTFont(
            "Arial",
            r"C:\Windows\Fonts\arial.ttf"
        )
    )

    pdfmetrics.registerFont(
        TTFont(
            "Arial-Bold",
            r"C:\Windows\Fonts\arialbd.ttf"
        )
    )

    POLICE_NORMALE = "Arial"
    POLICE_GRAS = "Arial-Bold"

except Exception:

    POLICE_NORMALE = "Helvetica"
    POLICE_GRAS = "Helvetica-Bold"


# ============================================================
# COULEURS
# ============================================================

VERT = colors.HexColor(
    "#5B8E73"
)

VERT_PALE = colors.HexColor(
    "#EDF4EF"
)

VERT_TRES_PALE = colors.HexColor(
    "#F7FAF8"
)

TEXTE = colors.HexColor(
    "#24312A"
)

TEXTE_SECONDAIRE = colors.HexColor(
    "#718078"
)

TEXTE_LEGER = colors.HexColor(
    "#A0AAA5"
)

BORDURE = colors.HexColor(
    "#E4EAE6"
)

BLANC = colors.white


# ============================================================
# OUTILS
# ============================================================

def formater_temps(
    centisecondes
):

    if centisecondes is None:
        return "-"

    heures = (
        centisecondes
        // 360000
    )

    minutes = (
        centisecondes
        // 6000
    ) % 60

    secondes = (
        centisecondes
        // 100
    ) % 60

    centiemes = (
        centisecondes
        % 100
    )

    return (
        f"{heures:02d}:"
        f"{minutes:02d}:"
        f"{secondes:02d}."
        f"{centiemes:02d}"
    )


def formater_ecart(
    centisecondes
):

    if (
        centisecondes is None
        or centisecondes == 0
    ):
        return "—"

    return (
        "+"
        + formater_temps(
            centisecondes
        )
    )


# ============================================================
# EXPORT PDF
# ============================================================

def exporter_pdf(
    resultat,
    titre,
    course
):

    sortie = io.BytesIO()


    largeur_page, hauteur_page = landscape(A4)


    document = SimpleDocTemplate(

        sortie,

        pagesize=landscape(A4),

        leftMargin=20 * mm,
        rightMargin=20 * mm,

        topMargin=16 * mm,
        bottomMargin=16 * mm
    )


    elements = []


    # ========================================================
    # STYLES
    # ========================================================

    style_logo = ParagraphStyle(

        "Logo",

        fontName=POLICE_GRAS,

        fontSize=12,

        leading=14,

        textColor=VERT,

        alignment=TA_LEFT
    )


    style_header_droite = ParagraphStyle(

        "HeaderDroite",

        fontName=POLICE_GRAS,

        fontSize=8,

        leading=10,

        textColor=TEXTE_SECONDAIRE,

        alignment=TA_RIGHT
    )


    style_titre = ParagraphStyle(

        "Titre",

        fontName=POLICE_GRAS,

        fontSize=28,

        leading=31,

        textColor=TEXTE,

        alignment=TA_LEFT
    )


    style_sous_titre = ParagraphStyle(

        "SousTitre",

        fontName=POLICE_NORMALE,

        fontSize=9.5,

        leading=12,

        textColor=TEXTE_SECONDAIRE,

        alignment=TA_LEFT
    )


    style_entete = ParagraphStyle(

        "Entete",

        fontName=POLICE_GRAS,

        fontSize=7.5,

        leading=9,

        textColor=TEXTE_SECONDAIRE,

        alignment=TA_CENTER
    )


    style_entete_gauche = ParagraphStyle(

        "EnteteGauche",

        fontName=POLICE_GRAS,

        fontSize=7.5,

        leading=9,

        textColor=TEXTE_SECONDAIRE,

        alignment=TA_CENTER
    )


    style_position = ParagraphStyle(

        "Position",

        fontName=POLICE_GRAS,

        fontSize=10,

        leading=12,

        textColor=VERT,

        alignment=TA_CENTER
    )


    style_dossard = ParagraphStyle(

        "Dossard",

        fontName=POLICE_GRAS,

        fontSize=8,

        leading=10,

        textColor=TEXTE_SECONDAIRE,

        alignment=TA_CENTER
    )


    style_nom = ParagraphStyle(

        "Nom",

        fontName=POLICE_GRAS,

        fontSize=10,

        leading=12,

        textColor=TEXTE,

        alignment=TA_CENTER
    )


    style_meta = ParagraphStyle(

        "Meta",

        fontName=POLICE_NORMALE,

        fontSize=7.5,

        leading=9,

        textColor=TEXTE_SECONDAIRE,

        alignment=TA_CENTER
    )


    style_temps = ParagraphStyle(

        "Temps",

        fontName=POLICE_GRAS,

        fontSize=11,

        leading=13,

        textColor=TEXTE,

        alignment=TA_RIGHT
    )


    style_ecart = ParagraphStyle(

        "Ecart",

        fontName=POLICE_NORMALE,

        fontSize=9,

        leading=11,

        textColor=TEXTE_SECONDAIRE,

        alignment=TA_RIGHT
    )


    style_footer = ParagraphStyle(

        "Footer",

        fontName=POLICE_NORMALE,

        fontSize=7,

        leading=9,

        textColor=TEXTE_LEGER,

        alignment=TA_CENTER
    )


    # ========================================================
    # HEADER
    # ========================================================

    header = Table(

        [
            [

                Paragraph(
                    f"{course.nom} · {course.date.strftime('%d/%m/%Y')}",
                    style_logo
                ),

                Paragraph(
                    "RÉSULTATS",
                    style_header_droite
                )

            ]
        ],

        colWidths=[

            70 * mm,

            largeur_page - 110 * mm

        ]

    )


    header.setStyle(

        TableStyle(
            [

                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    0
                ),

                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    0
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    0
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    8
                ),

                (
                    "LINEBELOW",
                    (0, 0),
                    (-1, -1),
                    0.8,
                    BORDURE
                )

            ]
        )

    )


    elements.append(
        header
    )


    elements.append(
        Spacer(
            1,
            14
        )
    )


    # ========================================================
    # TITRE
    # ========================================================

    elements.append(
        Paragraph(
            titre,
            style_titre
        )
    )


    elements.append(
        Spacer(
            1,
            3
        )
    )


    nombre_coureurs = len(
        resultat
    )


    texte_coureurs = (

        f"{nombre_coureurs} "

        + (
            "coureur classé"
            if nombre_coureurs == 1
            else "coureurs classés"
        )

    )


    elements.append(
        Paragraph(
            texte_coureurs,
            style_sous_titre
        )
    )


    elements.append(
        Spacer(
            1,
            14
        )
    )


    # ========================================================
    # TABLEAU
    # ========================================================

    donnees = []


    # --------------------------------------------------------
    # EN-TÊTE
    # --------------------------------------------------------

    donnees.append(

        [

            Paragraph(
                "POS.",
                style_entete
            ),

            Paragraph(
                "DOSSARD",
                style_entete
            ),

            Paragraph(
                "COUREUR",
                style_entete_gauche
            ),

            Paragraph(
                "SEXE",
                style_entete
            ),

            Paragraph(
                "CATÉGORIE",
                style_entete
            ),

            Paragraph(
                "TEMPS",
                style_entete
            ),

            Paragraph(
                "ÉCART",
                style_entete
            )

        ]

    )


    # --------------------------------------------------------
    # COUREURS
    # --------------------------------------------------------

    for coureur in resultat:

        categorie = (

            coureur.get(
                "categorie_export"
            )

            or coureur.get(
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


        donnees.append(

            [

                Paragraph(
                    str(
                        coureur["position"]
                    ),
                    style_position
                ),

                Paragraph(
                    dossard,
                    style_dossard
                ),

                Paragraph(
                    nom,
                    style_nom
                ),

                Paragraph(
                    coureur.get(
                        "sexe",
                        "-"
                    ),
                    style_meta
                ),

                Paragraph(
                    categorie,
                    style_meta
                ),

                Paragraph(
                    formater_temps(
                        coureur[
                            "temps_centisecondes"
                        ]
                    ),
                    style_temps
                ),

                Paragraph(
                    formater_ecart(
                        coureur[
                            "ecart_centisecondes"
                        ]
                    ),
                    style_ecart
                )

            ]

        )


    # ========================================================
    # DIMENSIONS
    # ========================================================

    table = Table(

        donnees,

        colWidths=[

            16 * mm,
            24 * mm,
            68 * mm,
            18 * mm,
            38 * mm,
            34 * mm,
            34 * mm

        ],

        repeatRows=1,

        hAlign="CENTER"
    )


    # ========================================================
    # STYLE
    # ========================================================

    styles_table = [

        # ----------------------------------------------------
        # EN-TÊTE
        # ----------------------------------------------------

        (
            "BACKGROUND",
            (0, 0),
            (-1, 0),
            VERT_PALE
        ),

        (
            "LINEBELOW",
            (0, 0),
            (-1, 0),
            1,
            VERT
        ),


        # ----------------------------------------------------
        # CELLULES
        # ----------------------------------------------------

        (
            "VALIGN",
            (0, 0),
            (-1, -1),
            "MIDDLE"
        ),

        (
            "LEFTPADDING",
            (0, 0),
            (-1, -1),
            7
        ),

        (
            "RIGHTPADDING",
            (0, 0),
            (-1, -1),
            7
        ),

        (
            "TOPPADDING",
            (0, 0),
            (-1, -1),
            8
        ),

        (
            "BOTTOMPADDING",
            (0, 0),
            (-1, -1),
            8
        ),


        # ----------------------------------------------------
        # SEPARATIONS
        # ----------------------------------------------------

        (
            "LINEBELOW",
            (0, 1),
            (-1, -1),
            0.4,
            BORDURE
        )

    ]


    # ========================================================
    # ALTERNANCE DES LIGNES
    # ========================================================

    for index in range(
        1,
        len(donnees)
    ):

        if index % 2 == 0:

            styles_table.append(

                (
                    "BACKGROUND",
                    (0, index),
                    (-1, index),
                    VERT_TRES_PALE
                )

            )

        else:

            styles_table.append(

                (
                    "BACKGROUND",
                    (0, index),
                    (-1, index),
                    BLANC
                )

            )


    # ========================================================
    # PREMIER
    # ========================================================

    if len(donnees) > 1:

        styles_table.append(

            (
                "BACKGROUND",
                (0, 1),
                (-1, 1),
                VERT_PALE
            )

        )


    table.setStyle(

        TableStyle(
            styles_table
        )

    )


    elements.append(
        table
    )


    # ========================================================
    # PIED DE PAGE
    # ========================================================

    elements.append(
        Spacer(
            1,
            12
        )
    )


    elements.append(

        Paragraph(
            "ChronoLive · Résultats officiels",
            style_footer
        )

    )


    # ========================================================
    # GENERATION
    # ========================================================

    document.build(
        elements
    )


    sortie.seek(0)

    return sortie.getvalue()

