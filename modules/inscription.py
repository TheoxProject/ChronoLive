#-----------
# MODULE 1 - INSCRIPTION
#-----------
# Gestion des inscriptions et des informations
# relatives aux coureurs de la course.
#
# Fonctionnalités :
# - affichage de la liste des coureurs
# - ajout d'un coureur
# - modification d'un coureur
# - suppression d'un coureur
#
# Routes :
# - /
# - /ajouter_coureur
# - /modifier_coureur/<id>
# - /supprimer_coureur/<id>
#-----------

from datetime import datetime

from flask import (
    Blueprint,
    redirect,
    render_template,
    request,
    url_for,
)

from config import CATEGORIES, CATEGORIES_FFC, STATUT_INSCRIT, STATUT_PRET
from database import Session
from models import Arrivee, Course, Coureur


inscription_bp = Blueprint(
    "inscription",
    __name__
)


COURSE_ID = 1


@inscription_bp.route("/inscription")
def inscription():
    # Affiche la page d'inscription
    # avec les coureurs de la course.

    session = Session()

    try:
        course = (
            session.query(Course)
            .filter_by(id=COURSE_ID)
            .first()
        )

        coureurs = (
            session.query(Coureur)
            .filter_by(course_id=COURSE_ID)
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
        )

    finally:
        session.close()


@inscription_bp.route(
    "/ajouter_coureur",
    methods=["POST"]
)
def ajouter_coureur():
    # Ajoute un nouveau coureur dans la base.

    session = Session()

    try:
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

        date_naissance = datetime.strptime(
            date_naissance_str,
            "%Y-%m-%d"
        ).date()

        coureur = Coureur(
            nom=nom,
            prenom=prenom,
            sexe=sexe,
            date_naissance=date_naissance,
            licence=licence,
            club=club,
            categorie=categorie,
            categorie_ffc=categorie_ffc,
            course_id=COURSE_ID,
        )

        session.add(coureur)
        session.commit()

    except Exception:
        # Annule les modifications en cas d'erreur.
        session.rollback()

    finally:
        session.close()

    return redirect(
        url_for(
            "inscription.inscription"
        )
    )


@inscription_bp.route(
    "/modifier_coureur/<int:coureur_id>",
    methods=["POST"]
)
def modifier_coureur(coureur_id):
    # Modifie les informations d'un coureur.

    session = Session()

    try:
        coureur = (
            session.query(Coureur)
            .filter_by(
                id=coureur_id,
                course_id=COURSE_ID
            )
            .first()
        )

        if coureur is None:
            return redirect(
                url_for(
                    "inscription.inscription"
                )
            )

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

        coureur.licence = (
            request.form.get(
                "licence",
                ""
            ).strip()
            or None
        )

        coureur.club = (
            request.form.get(
                "club",
                ""
            ).strip()
            or None
        )

        coureur.categorie = request.form.get(
            "categorie",
            ""
        ).strip()

        coureur.categorie_ffc = (
            request.form.get(
                "categorie_ffc",
                ""
            ).strip()
            or None
        )

        dossard = request.form.get(
            "dossard",
            ""
        ).strip()

        if dossard:
            coureur.dossard = int(dossard)
        else:
            coureur.dossard = None

        heure_depart = request.form.get(
            "heure_depart",
            ""
        ).strip()

        if heure_depart:
            try:
                coureur.heure_depart = datetime.strptime(
                        heure_depart,
                        "%H:%M:%S"
                    ).time()
                
            except ValueError:
                coureur.heure_depart = datetime.strptime(
                        heure_depart,
                        "%H:%M"
                    ).time()
            
        else:
            coureur.heure_depart = None

        # Met à jour le statut si le départ est configuré.
        if coureur.statut in (STATUT_INSCRIT,STATUT_PRET):
            if (
                coureur.dossard is not None
                and coureur.heure_depart is not None
            ):
                coureur.statut = STATUT_PRET
            else:
                coureur.statut = STATUT_INSCRIT

        session.commit()

    except Exception as erreur:
        # Annule les modifications en cas d'erreur.
        session.rollback()

        return redirect(
            url_for(
                "inscription.inscription",
                erreur=f"Erreur lors de la modification : {erreur}"
            )
    )

    finally:
        session.close()

    return redirect(
        url_for(
            "inscription.inscription"
        )
    )


@inscription_bp.route(
    "/supprimer_coureur/<int:coureur_id>",
    methods=["POST"]
)
def supprimer_coureur(coureur_id):
    # Supprime un coureur et son éventuelle arrivée.

    session = Session()

    try:
        coureur = (
            session.query(Coureur)
            .filter_by(
                id=coureur_id,
                course_id=COURSE_ID
            )
            .first()
        )

        if coureur is None:
            return redirect(
                url_for(
                    "inscription.inscription"
                )
            )

        # Supprime une éventuelle arrivée liée
        # au dossard du coureur.
        if coureur.dossard is not None:
            session.query(Arrivee).filter_by(
                course_id=COURSE_ID,
                dossard_coureur=coureur.dossard
            ).delete()

        session.delete(coureur)

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