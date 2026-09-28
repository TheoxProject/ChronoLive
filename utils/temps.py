#-----------
# GESTION DU TEMPS
#-----------
# Fonctions utilisées pour le chronométrage.
#
# Calcul des temps en centisecondes et
# formatage des temps pour l'affichage.
#-----------



def calculer_temps_centisecondes(
    heure_depart,
    timestamp_arrivee
):
    # Calcule le temps de course en centisecondes.

    arrivee_secondes = (
        timestamp_arrivee.hour * 3600
        + timestamp_arrivee.minute * 60
        + timestamp_arrivee.second
        + timestamp_arrivee.microsecond / 1_000_000
    )

    depart_secondes = (
        heure_depart.hour * 3600
        + heure_depart.minute * 60
        + heure_depart.second
        + heure_depart.microsecond / 1_000_000
    )

    difference = arrivee_secondes - depart_secondes

    return max(
        0,
        round(difference * 100)
    )


def formater_temps(total_centisecondes):
    # Transforme un temps en centisecondes
    # au format HH:MM:SS.CC.

    if total_centisecondes is None:
        return "--:--:--.--"

    heures = total_centisecondes // 360000

    reste = total_centisecondes % 360000

    minutes = reste // 6000

    reste %= 6000

    secondes = reste // 100

    centiemes = reste % 100

    return (
        f"{heures:02d}:"
        f"{minutes:02d}:"
        f"{secondes:02d}."
        f"{centiemes:02d}"
    )