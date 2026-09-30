# ------------------------------------------------------------
# MODULE 1 - INSCRIPTION
# ------------------------------------------------------------
# Gestion des inscriptions et des informations
# relatives aux coureurs de la course.
#
# Fonctionnalités :
# - affichage de la liste des coureurs
# - ajout d'un coureur
# - modification d'un coureur
# - suppression d'un coureur
#
# Une base SQLite correspond à UNE seule course.
# La course active est donc déterminée par la base sélectionnée
# au lancement de ChronoLive.
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
    CATEGORIES,
    CATEGORIES_FFC,
    STATUT_INSCRIT,
    STATUT_PRET,
    TYPE_CRITERIUM,
    TYPE_GRIMPEE,
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


# ------------------------------------------------------------
# BLUEPRINT
# ------------------------------------------------------------

inscription_bp = Blueprint(
    "inscription",
    __name__
)


# ------------------------------------------------------------
# COURSE ACTIVE
# ------------------------------------------------------------

def recuperer_course(
    session
):
    """
    Retourne l'unique course présente dans la base active.
    """

    return (
        session.query(
            Course
        )
        .first()
    )


# ------------------------------------------------------------
# PAGE D'INSCRIPTION
# ------------------------------------------------------------

@inscription_bp.route(
    "/inscription"
)
def inscription():

    # Aucune course ne doit être utilisée avant sa sélection.
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

        coureurs = (
            session.query(
                Coureur
            )
            .order_by(
                Coureur.nom,
                Coureur.prenom
            )
            .all()
        )

        return render_template(
            "inscription.html",
            coureurs=coureurs,
            course_nom=course.nom,
            course_date=course.date,
            course_lieu=course.lieu,
            categories=CATEGORIES,
            categories_ffc=CATEGORIES_FFC,
            course_type=course.type_course,
        )

    finally:

        session.close()


# ------------------------------------------------------------
# AJOUTER UN COUREUR
# ------------------------------------------------------------

@inscription_bp.route(
    "/ajouter_coureur",
    methods=["POST"]
)
def ajouter_coureur():

    if not base_est_initialisee():

        return redirect(
            url_for(
                "accueil"
            )
        )

    session = Session()

    try:

        # ----------------------------------------------------
        # COURSE
        # ----------------------------------------------------

        course = recuperer_course(
            session
        )

        if course is None:

            return redirect(
                url_for(
                    "inscription.inscription"
                )
            )

        # ----------------------------------------------------
        # DONNEES DU COUREUR
        # ----------------------------------------------------

        nom = request.form.get(
            "nom",
            ""
        ).strip()

        prenom = request.form.get(
            "prenom",
            ""
        ).strip()

        sexe = request.form.get(
            "sexe",
            ""
        ).strip()

        date_naissance_str = request.form.get(
            "date_naissance",
            ""
        ).strip()

        licence = (
            request.form.get(
                "licence",
                ""
            ).strip()
            or None
        )

        club = (
            request.form.get(
                "club",
                ""
            ).strip()
            or None
        )

        categorie = request.form.get(
            "categorie",
            ""
        ).strip()

        categorie_ffc = (
            request.form.get(
                "categorie_ffc",
                ""
            ).strip()
            or None
        )

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not nom or not prenom:

            return redirect(
                url_for(
                    "inscription.inscription"
                )
            )

        if sexe not in (
            "M",
            "F",
        ):

            return redirect(
                url_for(
                    "inscription.inscription"
                )
            )

        if categorie not in CATEGORIES:

            return redirect(
                url_for(
                    "inscription.inscription"
                )
            )

        if (
            categorie_ffc
            and categorie_ffc not in CATEGORIES_FFC
        ):

            return redirect(
                url_for(
                    "inscription.inscription"
                )
            )

        if not date_naissance_str:

            return redirect(
                url_for(
                    "inscription.inscription"
                )
            )

        try:

            date_naissance = datetime.strptime(
                date_naissance_str,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            return redirect(
                url_for(
                    "inscription.inscription"
                )
            )

        # ----------------------------------------------------
        # HEURE DE DEPART
        # ----------------------------------------------------
        # CLM :
        #   départ individuel à définir ensuite.
        #
        # Grimpée / Critérium :
        #   tous les coureurs prennent le départ commun
        #   défini dans Course.heure_depart.
        # ----------------------------------------------------

        heure_depart = None

        if course.type_course in (
            TYPE_GRIMPEE,
            TYPE_CRITERIUM,
        ):

            heure_depart = (
                course.heure_depart
            )

        # ----------------------------------------------------
        # CREATION
        # ----------------------------------------------------

        coureur = Coureur(
            nom=nom,
            prenom=prenom,
            sexe=sexe,
            date_naissance=date_naissance,
            licence=licence,
            club=club,
            categorie=categorie,
            categorie_ffc=categorie_ffc,
            heure_depart=heure_depart,
        )

        session.add(
            coureur
        )

        session.commit()

    except Exception:

        session.rollback()

    finally:

        session.close()

    return redirect(
        url_for(
            "inscription.inscription"
        )
    )


# ------------------------------------------------------------
# MODIFIER UN COUREUR
# ------------------------------------------------------------

@inscription_bp.route(
    "/modifier_coureur/<int:coureur_id>",
    methods=["POST"]
)
def modifier_coureur(
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

        # ----------------------------------------------------
        # RECHERCHE DU COUREUR
        # ----------------------------------------------------
        # Plus besoin de course_id :
        # la DB active correspond déjà à une seule course.
        # ----------------------------------------------------

        coureur = (
            session.query(
                Coureur
            )
            .filter_by(
                id=coureur_id
            )
            .first()
        )

        if coureur is None:

            return redirect(
                url_for(
                    "inscription.inscription"
                )
            )

        # ----------------------------------------------------
        # INFORMATIONS GENERALES
        # ----------------------------------------------------

        coureur.nom = request.form.get(
            "nom",
            ""
        ).strip()

        coureur.prenom = request.form.get(
            "prenom",
            ""
        ).strip()

        coureur.sexe = request.form.get(
            "sexe",
            ""
        ).strip()

        # ----------------------------------------------------
        # DATE DE NAISSANCE
        # ----------------------------------------------------

        date_naissance = request.form.get(
            "date_naissance",
            ""
        ).strip()

        if date_naissance:

            coureur.date_naissance = (
                datetime.strptime(
                    date_naissance,
                    "%Y-%m-%d"
                ).date()
            )

        # ----------------------------------------------------
        # LICENCE
        # ----------------------------------------------------

        coureur.licence = (
            request.form.get(
                "licence",
                ""
            ).strip()
            or None
        )

        # ----------------------------------------------------
        # CLUB
        # ----------------------------------------------------

        coureur.club = (
            request.form.get(
                "club",
                ""
            ).strip()
            or None
        )

        # ----------------------------------------------------
        # CATEGORIES
        # ----------------------------------------------------

        categorie = request.form.get(
            "categorie",
            ""
        ).strip()

        categorie_ffc = (
            request.form.get(
                "categorie_ffc",
                ""
            ).strip()
            or None
        )

        if categorie in CATEGORIES:

            coureur.categorie = (
                categorie
            )

        if (
            categorie_ffc is None
            or categorie_ffc in CATEGORIES_FFC
        ):

            coureur.categorie_ffc = (
                categorie_ffc
            )

        # ----------------------------------------------------
        # DOSSARD
        # ----------------------------------------------------

        dossard = request.form.get(
            "dossard",
            ""
        ).strip()

        if dossard:

            coureur.dossard = int(
                dossard
            )

        else:

            coureur.dossard = None

        # ----------------------------------------------------
        # HEURE DE DEPART
        # ----------------------------------------------------

        heure_depart = request.form.get(
            "heure_depart",
            ""
        ).strip()

        if heure_depart:

            try:

                coureur.heure_depart = (
                    datetime.strptime(
                        heure_depart,
                        "%H:%M:%S"
                    ).time()
                )

            except ValueError:

                coureur.heure_depart = (
                    datetime.strptime(
                        heure_depart,
                        "%H:%M"
                    ).time()
                )

        else:

            coureur.heure_depart = None

        # ----------------------------------------------------
        # COURSE
        # ----------------------------------------------------

        course = recuperer_course(
            session
        )

        if course is None:

            return redirect(
                url_for(
                    "inscription.inscription"
                )
            )

        # ----------------------------------------------------
        # DEPART COMMUN
        # ----------------------------------------------------
        # Pour une Grimpée ou un Critérium,
        # l'heure de départ du coureur doit toujours
        # correspondre à celle de la course.
        # ----------------------------------------------------

        if course.type_course in (
            TYPE_GRIMPEE,
            TYPE_CRITERIUM,
        ):

            coureur.heure_depart = (
                course.heure_depart
            )

        # ----------------------------------------------------
        # STATUT
        # ----------------------------------------------------

        if coureur.statut in (
            STATUT_INSCRIT,
            STATUT_PRET,
        ):

            if (
                coureur.dossard is not None
                and coureur.heure_depart is not None
            ):

                coureur.statut = (
                    STATUT_PRET
                )

            else:

                coureur.statut = (
                    STATUT_INSCRIT
                )

        session.commit()

    except Exception as erreur:

        session.rollback()

        return redirect(
            url_for(
                "inscription.inscription",
                erreur=(
                    f"Erreur lors de la modification : "
                    f"{erreur}"
                ),
            )
        )

    finally:

        session.close()

    return redirect(
        url_for(
            "inscription.inscription"
        )
    )


# ------------------------------------------------------------
# SUPPRIMER UN COUREUR
# ------------------------------------------------------------

@inscription_bp.route(
    "/supprimer_coureur/<int:coureur_id>",
    methods=["POST"]
)
def supprimer_coureur(
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
            .filter_by(
                id=coureur_id
            )
            .first()
        )

        if coureur is None:

            return redirect(
                url_for(
                    "inscription.inscription"
                )
            )

        # ----------------------------------------------------
        # SUPPRESSION DE L'EVENTUELLE ARRIVEE
        # ----------------------------------------------------
        # La DB correspondant déjà à une seule course,
        # aucun course_id n'est nécessaire.
        # ----------------------------------------------------

        if coureur.dossard is not None:

            (
                session.query(
                    Arrivee
                )
                .filter_by(
                    dossard_coureur=coureur.dossard
                )
                .delete(
                    synchronize_session=False
                )
            )

        session.delete(
            coureur
        )

        session.commit()

    except Exception:

        session.rollback()

    finally:

        session.close()

    return redirect(
        url_for(
            "inscription.inscription"
        )
    )

