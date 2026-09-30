# ------------------------------------------------------------
# MODULE 2 - CHRONOMÉTRAGE
# ------------------------------------------------------------
# Gestion des arrivées pendant la course.
#
# Fonctionnalités :
# - affichage de l'écran de chronométrage
# - enregistrement d'une arrivée
# - enregistrement d'une arrivée manquée
# - association d'une arrivée à un dossard
# - suppression d'une arrivée
# - affichage des prochains partants
# - gestion des statuts des coureurs
#
# Le timestamp enregistré lors de l'appui sur
# "ARRIVÉE" constitue la source de vérité.
#
# Modes de chronométrage :
#
# MANUEL :
#   timestamp seul
#       ↓
#   attribution manuelle du dossard
#       ↓
#   traitement de l'arrivée
#
# ARRIVÉE MANQUÉE :
#   heure saisie manuellement
#       ↓
#   création d'un timestamp
#       ↓
#   attribution manuelle du dossard
#       ↓
#   traitement de l'arrivée
#
# AUTOMATIQUE :
#   dossard + timestamp
#       ↓
#   traitement de l'arrivée
#
# Une base SQLite correspond à UNE seule course.
# Il n'y a donc plus de course_id dans les requêtes.
#
# Routes :
# - /chronometrage
# - /enregistrer_arrivee
# - /enregistrer_arrivee_manquee
# - /associer_arrivee/<id>
# - /supprimer_arrivee/<id>
# - /modifier_statut/<id>
# ------------------------------------------------------------

from datetime import datetime

from flask import (
    Blueprint,
    redirect,
    render_template,
    request,
    url_for,
)

from config import (
    STATUT_INSCRIT,
    STATUT_PRET,
    STATUT_ARRIVE,
    STATUT_DNS,
    STATUT_DNF,
    STATUT_DSQ,
)

from database import (
    Session,
    base_est_initialisee,
)

from models import (
    Arrivee,
    Course,
    Coureur,
)

from modules.classement_live import notifier_classement

from utils.temps import calculer_temps_centisecondes
from utils.temps import formater_temps


chronometrage_bp = Blueprint(
    "chronometrage",
    __name__
)


# ------------------------------------------------------------
# COURSE ACTIVE
# ------------------------------------------------------------

def recuperer_course(
    session
):
    """
    Retourne l'unique course présente
    dans la base actuellement chargée.
    """

    return (
        session.query(
            Course
        )
        .first()
    )


# ------------------------------------------------------------
# TRAITEMENT COMMUN D'UNE ARRIVÉE
# ------------------------------------------------------------

def traiter_arrivee(session, arrivee, dossard):
    """
    Traite une arrivée une fois que le dossard est connu.

    Cette fonction constitue le cœur commun du chronométrage.

    Elle peut être appelée :
    - depuis le mode manuel après attribution du dossard ;
    - depuis une arrivée manquée après attribution du dossard ;
    - depuis le mode automatique. (en developement)

    Le timestamp de l'objet Arrivee reste la source de vérité.
    """

    coureur = (
        session.query(
            Coureur
        )
        .filter_by(
            dossard=dossard
        )
        .first()
    )

    if coureur is None:

        raise ValueError(
            f"Dossard {dossard} inconnu"
        )

    if coureur.heure_depart is None:

        raise ValueError(
            f"{coureur.prenom} {coureur.nom} "
            "n'a pas d'heure de départ"
        )

    # Vérifie que le coureur n'a pas déjà une autre arrivée.
    arrivee_existante = (
        session.query(
            Arrivee
        )
        .filter(
            Arrivee.dossard_coureur == dossard,
            Arrivee.id != arrivee.id,
        )
        .first()
    )

    if arrivee_existante is not None:

        raise ValueError(
            f"Le dossard {dossard} "
            "possède déjà une arrivée"
        )

    # Seuls les coureurs prêts peuvent être classés.
    if coureur.statut != STATUT_PRET:

        raise ValueError(
            f"{coureur.prenom} {coureur.nom} "
            "n'est pas dans l'état prêt"
        )

    # Association entre l'arrivée et le coureur.
    arrivee.dossard_coureur = dossard

    # Sauvegarde de l'heure d'arrivée du coureur.
    coureur.heure_arrivee = (
        arrivee.timestamp.time()
    )

    # Calcul du temps de course.
    coureur.temps_centisecondes = (
        calculer_temps_centisecondes(
            coureur.heure_depart,
            arrivee.timestamp
        )
    )

    coureur.statut = STATUT_ARRIVE

    session.commit()

    # Mise à jour immédiate du classement public.
    notifier_classement()


# ------------------------------------------------------------
# FUTUR CHRONOMÉTRAGE AUTOMATIQUE
# ------------------------------------------------------------

def enregistrer_arrivee_auto(
    dossard,
    timestamp
):
    """
    Point d'entrée du futur chronométrage automatique.

    Le système automatique devra fournir :
    - le dossard détecté ;
    - le timestamp de détection.

    La logique sera ensuite reliée à traiter_arrivee().
    """

    pass


# ------------------------------------------------------------
# ÉCRAN DE CHRONOMÉTRAGE
# ------------------------------------------------------------

@chronometrage_bp.route(
    "/chronometrage"
)
def chronometrage():
    # Affiche l'écran du chronométreur
    # avec les arrivées et les coureurs à gérer.

    if not base_est_initialisee():

        return redirect(
            url_for(
                "accueil"
            )
        )

    session = Session()

    try:

        course = recuperer_course(
            session
        )

        if course is None:

            return (
                "Aucune course valide n'est présente "
                "dans la base active.",
                500,
            )

        # ----------------------------------------------------
        # ARRIVEES
        # ----------------------------------------------------

        arrivees = (
            session.query(
                Arrivee
            )
            .order_by(
                Arrivee.id.desc()
            )
            .all()
        )

        arrivees_a_associer = []

        arrivees_associees = []

        for arrivee in arrivees:

            # Arrivée enregistrée mais sans dossard.
            if arrivee.dossard_coureur is None:

                arrivees_a_associer.append(
                    arrivee
                )

                continue

            coureur = (
                session.query(
                    Coureur
                )
                .filter_by(
                    dossard=arrivee.dossard_coureur
                )
                .first()
            )

            if coureur is None:

                continue

            arrivees_associees.append({
                "id": arrivee.id,
                "dossard": coureur.dossard,
                "nom": coureur.nom,
                "prenom": coureur.prenom,
                "categorie": coureur.categorie,
                "heure_depart": coureur.heure_depart,
                "timestamp": arrivee.timestamp,
                "temps": formater_temps(
                    coureur.temps_centisecondes
                ),
            })

        # --------------------------------------------------
        # PROCHAINS PARTANTS
        # --------------------------------------------------

        maintenant = datetime.now().time()

        prochains_partants = (
            session.query(
                Coureur
            )
            .filter(
                Coureur.dossard.isnot(None),
                Coureur.heure_depart.isnot(None),
                Coureur.statut == STATUT_PRET,
                Coureur.heure_depart > maintenant,
            )
            .order_by(
                Coureur.heure_depart.asc()
            )
            .all()
        )

        # --------------------------------------------------
        # COUREURS À GÉRER
        # --------------------------------------------------
        # Tous les coureurs de la base active sont affichés.
        # Le filtrage est ensuite effectué côté navigateur.

        coureurs_db = (
            session.query(
                Coureur
            )
            .filter(
                Coureur.dossard.isnot(None),
            )
            .order_by(
                Coureur.dossard.asc()
            )
            .all()
        )

        coureurs_a_gerer = []

        for coureur in coureurs_db:

            # Le statut "en course" est dérivé de
            # l'heure de départ et n'est pas stocké en base.

            en_course = (
                coureur.statut == STATUT_PRET
                and coureur.heure_depart is not None
                and coureur.heure_depart <= maintenant
            )

            if en_course:

                statut_affichage = "EN COURSE"

            elif coureur.statut == STATUT_INSCRIT:

                statut_affichage = "INSCRIT"

            elif coureur.statut == STATUT_PRET:

                statut_affichage = "PRÊT"

            elif coureur.statut == STATUT_ARRIVE:

                statut_affichage = "ARRIVÉ"

            elif coureur.statut == STATUT_DNS:

                statut_affichage = "DNS"

            elif coureur.statut == STATUT_DNF:

                statut_affichage = "DNF"

            elif coureur.statut == STATUT_DSQ:

                statut_affichage = "DSQ"

            else:

                statut_affichage = coureur.statut

            coureurs_a_gerer.append({
                "id": coureur.id,
                "dossard": coureur.dossard,
                "nom": coureur.nom,
                "prenom": coureur.prenom,
                "statut": coureur.statut,
                "statut_affichage": statut_affichage,
                "en_course": en_course,
                "heure_depart": coureur.heure_depart,
            })

        return render_template(
            "chronometrage.html",
            course_nom=course.nom,
            course_lieu=course.lieu,
            course_date=course.date,
            arrivees_en_attente=arrivees_a_associer,
            arrivees_associees=arrivees_associees,
            prochains_partants=prochains_partants,
            coureurs_a_gerer=coureurs_a_gerer,
        )

    finally:

        session.close()


# ------------------------------------------------------------
# ENREGISTRER UNE ARRIVÉE - MODE MANUEL
# ------------------------------------------------------------

@chronometrage_bp.route(
    "/enregistrer_arrivee",
    methods=["POST"]
)
def enregistrer_arrivee():
    """
    Mode manuel.

    Le clic sur ARRIVÉE enregistre uniquement le timestamp.
    Aucun dossard n'est demandé à ce moment-là.
    """

    if not base_est_initialisee():

        return redirect(
            url_for(
                "accueil"
            )
        )

    session = Session()

    try:

        arrivee = Arrivee(
            timestamp=datetime.now(),
            dossard_coureur=None,
        )

        session.add(
            arrivee
        )

        session.commit()

    except Exception:

        session.rollback()

    finally:

        session.close()

    return redirect(
        url_for(
            "chronometrage.chronometrage"
        )
    )


# ------------------------------------------------------------
# ENREGISTRER UNE ARRIVÉE MANQUÉE
# ------------------------------------------------------------
@chronometrage_bp.route(
    "/enregistrer_arrivee_passee",
    methods=["POST"]
)
def enregistrer_arrivee_passee():
    """
    Enregistre manuellement l'heure de passage
    d'un coureur dont l'arrivée a été manquée.

    Le dossard n'est pas encore associé à ce stade.

    Le format attendu est :
        HH:MM:SS.CC

    Le champ ".CC" peut également être omis :
        HH:MM:SS

    La date utilisée pour le timestamp est celle
    de la course active.
    """

    if not base_est_initialisee():

        return redirect(
            url_for(
                "accueil"
            )
        )

    session = Session()

    try:

        # ----------------------------------------------------
        # COURSE ACTIVE
        # ----------------------------------------------------

        course = recuperer_course(
            session
        )

        if course is None:

            return redirect(
                url_for(
                    "chronometrage.chronometrage",
                    erreur="Aucune course active"
                )
            )

        # ----------------------------------------------------
        # RECUPERATION DE L'HEURE
        # ----------------------------------------------------

        heure_str = (
            request.form.get(
                "heure",
                ""
            )
            .strip()
        )

        # Compatibilité avec d'éventuels noms de champ
        # différents utilisés dans le template.
        if not heure_str:

            heure_str = (
                request.form.get(
                    "heure_arrivee",
                    ""
                )
                .strip()
            )

        if not heure_str:

            heure_str = (
                request.form.get(
                    "timestamp",
                    ""
                )
                .strip()
            )

        if not heure_str:

            return redirect(
                url_for(
                    "chronometrage.chronometrage",
                    erreur="Aucune heure d'arrivée renseignée"
                )
            )

        # ----------------------------------------------------
        # PARSING
        # ----------------------------------------------------
        # Formats acceptés :
        #   HH:MM:SS.CC
        #   HH:MM:SS
        #
        # Exemple :
        #   15:37:24.56
        #   15:37:24
        # ----------------------------------------------------

        if "." in heure_str:

            heure = datetime.strptime(
                heure_str,
                "%H:%M:%S.%f"
            ).time()

        else:

            heure = datetime.strptime(
                heure_str,
                "%H:%M:%S"
            ).time()

        # ----------------------------------------------------
        # DATE DE LA COURSE
        # ----------------------------------------------------

        date_course = course.date

        # Sécurité si course.date est exceptionnellement
        # un datetime au lieu d'un objet date.
        if isinstance(
            date_course,
            datetime
        ):

            date_course = date_course.date()

        if date_course is None:

            return redirect(
                url_for(
                    "chronometrage.chronometrage",
                    erreur="La date de la course est invalide"
                )
            )

        # ----------------------------------------------------
        # CREATION DE L'ARRIVEE
        # ----------------------------------------------------

        timestamp = datetime.combine(
            date_course,
            heure
        )

        arrivee = Arrivee(
            timestamp=timestamp,
            dossard_coureur=None,
        )

        session.add(
            arrivee
        )

        session.commit()

    except ValueError:

        session.rollback()

        return redirect(
            url_for(
                "chronometrage.chronometrage",
                erreur=(
                    "Heure invalide. "
                    "Format attendu : HH:MM:SS.CC"
                )
            )
        )

    except Exception:

        session.rollback()

        return redirect(
            url_for(
                "chronometrage.chronometrage",
                erreur="Impossible d'enregistrer l'arrivée"
            )
        )

    finally:

        session.close()

    return redirect(
        url_for(
            "chronometrage.chronometrage"
        )
    )


# ------------------------------------------------------------
# ASSOCIER UNE ARRIVÉE - MODE MANUEL
# ------------------------------------------------------------

@chronometrage_bp.route(
    "/associer_arrivee/<int:arrivee_id>",
    methods=["POST"]
)
def associer_arrivee(
    arrivee_id
):
    """
    Mode manuel.

    L'utilisateur attribue un dossard à une arrivée dont
    le timestamp a déjà été enregistré.

    Cette route est identique pour :
    - une arrivée normale ;
    - une arrivée manquée.
    """

    if not base_est_initialisee():

        return redirect(
            url_for(
                "accueil"
            )
        )

    session = Session()

    try:

        dossard_str = request.form.get(
            "dossard",
            ""
        ).strip()

        if not dossard_str.isdigit():

            return redirect(
                url_for(
                    "chronometrage.chronometrage",
                    erreur="Dossard invalide"
                )
            )

        dossard = int(
            dossard_str
        )

        arrivee = (
            session.query(
                Arrivee
            )
            .filter_by(
                id=arrivee_id
            )
            .first()
        )

        if arrivee is None:

            return redirect(
                url_for(
                    "chronometrage.chronometrage"
                )
            )

        # Le traitement réel de l'arrivée est désormais
        # centralisé dans traiter_arrivee().
        traiter_arrivee(
            session,
            arrivee,
            dossard,
        )

    except ValueError as erreur:

        session.rollback()

        return redirect(
            url_for(
                "chronometrage.chronometrage",
                erreur=str(erreur)
            )
        )

    except Exception:

        session.rollback()

    finally:

        session.close()

    return redirect(
        url_for(
            "chronometrage.chronometrage"
        )
    )


# ------------------------------------------------------------
# SUPPRIMER UNE ARRIVÉE
# ------------------------------------------------------------

@chronometrage_bp.route(
    "/supprimer_arrivee/<int:arrivee_id>",
    methods=["POST"]
)
def supprimer_arrivee(
    arrivee_id
):
    # Supprime une arrivée et remet le coureur
    # dans son état précédent l'arrivée.

    if not base_est_initialisee():

        return redirect(
            url_for(
                "accueil"
            )
        )

    session = Session()

    try:

        arrivee = (
            session.query(
                Arrivee
            )
            .filter_by(
                id=arrivee_id
            )
            .first()
        )

        if arrivee is None:

            return redirect(
                url_for(
                    "chronometrage.chronometrage"
                )
            )

        if arrivee.dossard_coureur is not None:

            coureur = (
                session.query(
                    Coureur
                )
                .filter_by(
                    dossard=arrivee.dossard_coureur
                )
                .first()
            )

            if coureur is not None:

                coureur.heure_arrivee = None

                coureur.temps_centisecondes = None

                coureur.statut = STATUT_PRET

        session.delete(
            arrivee
        )

        session.commit()

        # Mise à jour du classement public.
        notifier_classement()

    except Exception:

        session.rollback()

    finally:

        session.close()

    return redirect(
        url_for(
            "chronometrage.chronometrage"
        )
    )


# --------------------------------------------------
# MODIFICATION DU STATUT D'UN COUREUR
# --------------------------------------------------

@chronometrage_bp.route(
    "/modifier_statut/<int:coureur_id>",
    methods=["POST"]
)
def modifier_statut_coureur(
    coureur_id
):

    if not base_est_initialisee():

        return redirect(
            url_for(
                "accueil"
            )
        )

    session = Session()

    try:

        coureur = (
            session.query(
                Coureur
            )
            .filter(
                Coureur.id == coureur_id,
            )
            .first()
        )

        if coureur is None:

            return redirect(
                url_for(
                    "chronometrage.chronometrage"
                )
            )

        nouveau_statut = request.form.get(
            "statut"
        )

        maintenant = datetime.now().time()

        # --------------------------------------------------
        # DNS
        # --------------------------------------------------

        if nouveau_statut == STATUT_DNS:

            if coureur.statut == STATUT_INSCRIT:

                coureur.statut = STATUT_DNS

            elif coureur.statut == STATUT_PRET:

                if (
                    coureur.heure_depart is None
                    or coureur.heure_depart <= maintenant
                ):

                    return redirect(
                        url_for(
                            "chronometrage.chronometrage"
                        )
                    )

                coureur.statut = STATUT_DNS

            else:

                return redirect(
                    url_for(
                        "chronometrage.chronometrage"
                    )
                )

        # --------------------------------------------------
        # DNF
        # --------------------------------------------------

        elif nouveau_statut == STATUT_DNF:

            if (
                coureur.statut != STATUT_PRET
                or coureur.heure_depart is None
                or coureur.heure_depart > maintenant
            ):

                return redirect(
                    url_for(
                        "chronometrage.chronometrage"
                    )
                )

            coureur.statut = STATUT_DNF

        # --------------------------------------------------
        # DSQ
        # --------------------------------------------------

        elif nouveau_statut == STATUT_DSQ:

            if coureur.statut == STATUT_PRET:

                if (
                    coureur.heure_depart is None
                    or coureur.heure_depart > maintenant
                ):

                    return redirect(
                        url_for(
                            "chronometrage.chronometrage"
                        )
                    )

            elif coureur.statut != STATUT_ARRIVE:

                return redirect(
                    url_for(
                        "chronometrage.chronometrage"
                    )
                )

            coureur.statut = STATUT_DSQ

        # --------------------------------------------------
        # REMETTRE EN COURSE
        # --------------------------------------------------

        elif nouveau_statut == STATUT_PRET:

            if coureur.statut not in (
                STATUT_DNS,
                STATUT_DNF,
                STATUT_DSQ,
            ):

                return redirect(
                    url_for(
                        "chronometrage.chronometrage"
                    )
                )

            # Si une arrivée existe encore,
            # elle est supprimée pour revenir
            # à un état prêt cohérent.
            arrivee = (
                session.query(
                    Arrivee
                )
                .filter(
                    Arrivee.dossard_coureur
                    == coureur.dossard,
                )
                .first()
            )

            if arrivee is not None:

                session.delete(
                    arrivee
                )

            coureur.heure_arrivee = None

            coureur.temps_centisecondes = None

            coureur.statut = STATUT_PRET

        else:

            return redirect(
                url_for(
                    "chronometrage.chronometrage"
                )
            )

        session.commit()

        # Mise à jour du classement public.
        notifier_classement()

    except Exception:

        session.rollback()

    finally:

        session.close()

    return redirect(
        url_for(
            "chronometrage.chronometrage"
        )
    )