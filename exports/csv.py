import io
import csv


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
# EXPORT CSV
# ============================================================

def exporter_csv(
    resultat,
    type_classement
):

    sortie = io.StringIO(
        newline=""
    )


    writer = csv.writer(
        sortie,
        delimiter=";",
        lineterminator="\n"
    )


    writer.writerow([
        "Pos.",
        "Dossard",
        "Coureur",
        "Sexe",
        "Catégorie",
        "Temps",
        "Écart"
    ])


    for coureur in resultat:

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


        writer.writerow([

            coureur["position"],

            dossard,

            nom,

            coureur.get(
                "sexe",
                "-"
            ),

            categorie,

            formater_temps(
                coureur[
                    "temps_centisecondes"
                ]
            ),

            formater_ecart(
                coureur[
                    "ecart_centisecondes"
                ]
            )

        ])


    return sortie.getvalue().encode(
        "utf-8-sig"
    )

