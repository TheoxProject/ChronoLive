from models import Coureur


# ============================================================
# SEXES
# ============================================================

SEXES = {
    "M": "Hommes",
    "F": "Femmes"
}


# ============================================================
# CONSTRUCTION DES RESULTATS
# ============================================================

def construire_resultat(
    session,
    type_classement="scratch",
    valeur=None
):
    """
    Construit le classement demandé.

    Types disponibles :
        - scratch
        - categorie
        - categorie_ffc
        - sexe

    Si aucune valeur n'est fournie pour une catégorie,
    tous les coureurs sont conservés.
    """

    # ========================================================
    # REQUETE DE BASE
    # ========================================================

    requete = (
        session.query(Coureur)
        .filter(
            Coureur.temps_centisecondes != None
        )
    )


    # ========================================================
    # FILTRAGE
    # ========================================================

    # --------------------------------------------------------
    # SCRATCH
    # --------------------------------------------------------
    #
    # Aucun filtre supplémentaire.
    #

    if type_classement == "scratch":

        pass


    # --------------------------------------------------------
    # CATEGORIE
    # --------------------------------------------------------

    elif type_classement == "categorie":

        if valeur:

            requete = requete.filter(
                Coureur.categorie == valeur
            )


    # --------------------------------------------------------
    # CATEGORIE FFC
    # --------------------------------------------------------

    elif type_classement == "categorie_ffc":

        if valeur:

            requete = requete.filter(
                Coureur.categorie_ffc == valeur
            )


    # --------------------------------------------------------
    # SEXE
    # --------------------------------------------------------

    elif type_classement == "sexe":

        if valeur in SEXES:

            requete = requete.filter(
                Coureur.sexe == valeur
            )


    # ========================================================
    # TRI
    # ========================================================

    coureurs = (
        requete
        .order_by(
            Coureur.temps_centisecondes.asc()
        )
        .all()
    )


    # ========================================================
    # AUCUN RESULTAT
    # ========================================================

    if not coureurs:

        return []


    # ========================================================
    # MEILLEUR TEMPS
    # ========================================================

    meilleur_temps = (
        coureurs[0].temps_centisecondes
    )


    # ========================================================
    # CONSTRUCTION
    # ========================================================

    resultat = []


    for position, coureur in enumerate(
        coureurs,
        start=1
    ):

        ecart_centisecondes = (
            coureur.temps_centisecondes
            - meilleur_temps
        )


        resultat.append(
            {
                "position": position,

                "dossard": coureur.dossard,

                "nom": coureur.nom,

                "prenom": coureur.prenom,

                "club": coureur.club,

                "categorie": coureur.categorie,

                "categorie_ffc": (
                    coureur.categorie_ffc
                    or "-"
                ),

                "sexe": coureur.sexe,

                "heure_depart": coureur.heure_depart,

                "heure_arrivee": coureur.heure_arrivee,

                "temps_centisecondes": (
                    coureur.temps_centisecondes
                ),

                "ecart_centisecondes": (
                    ecart_centisecondes
                )
            }
        )


    return resultat

