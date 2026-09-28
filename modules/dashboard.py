#-----------
# MODULE - DASHBOARD
#-----------
# Tableau de bord de la course et surveillance du système.
#
# Fonctionnalités :
# - suivi de l'avancement de la course
# - suivi des inscriptions, départs et arrivées
# - suivi des coureurs prêts à partir
# - suivi des coureurs encore en course
# - récapitulatif des statuts des coureurs
# - surveillance de la base SQLite
# - surveillance du serveur public
# - surveillance des connexions SSE
# - affichage de la dernière arrivée
#-----------

from datetime import datetime
from time import monotonic
from socket import create_connection

from flask import Blueprint, jsonify, render_template
from sqlalchemy import func

from config import (
    PORT_PUBLIC,
    STATUT_PRET,
    STATUT_ARRIVE,
    STATUTS,
)
from database import Session
from models import Arrivee, Course, Coureur
from modules.classement_live import sse_clients


dashboard_bp = Blueprint(
    "dashboard",
    __name__
)


COURSE_ID = 1


DEBUT_APPLICATION = monotonic()


def verifier_serveur_public():
    # Vérifie que le port public de ChronoLive accepte une connexion.
    try:
        with create_connection(
            ("127.0.0.1", PORT_PUBLIC),
            timeout=0.5
        ):
            return True
    except OSError:
        return False


def formater_duree(secondes):
    # Formate une durée en HH:MM:SS.
    secondes = max(
        0,
        int(secondes)
    )

    heures = secondes // 3600

    minutes = (
        secondes % 3600
    ) // 60

    secondes = (
        secondes % 60
    )

    return (
        f"{heures:02d}:"
        f"{minutes:02d}:"
        f"{secondes:02d}"
    )


def construire_etat_dashboard():

    session = Session()

    try:

        course = (
            session.query(Course)
            .filter_by(
                id=COURSE_ID
            )
            .first()
        )

        if course is None:

            return {
                "database": True,
                "course": None,
                "systeme": {
                    "serveur_public":
                        verifier_serveur_public(),

                    "sse_clients":
                        len(sse_clients),

                    "uptime":
                        formater_duree(
                            monotonic()
                            - DEBUT_APPLICATION
                        ),
                },
            }


        # ------------------------------------------
        # STATISTIQUES
        # ------------------------------------------

        total_coureurs = (
            session.query(
                func.count(
                    Coureur.id
                )
            )
            .filter(
                Coureur.course_id
                == COURSE_ID
            )
            .scalar()
            or 0
        )


        departs_configures = (
            session.query(
                func.count(
                    Coureur.id
                )
            )
            .filter(
                Coureur.course_id
                == COURSE_ID,

                Coureur.heure_depart
                .isnot(None),
            )
            .scalar()
            or 0
        )


        # Heure actuelle utilisée pour déterminer les coureurs prêts et ceux déjà partis.
        maintenant = datetime.now().time()


        # Prêts à partir = statut prêt et départ à venir.
        coureurs_prets = (
            session.query(
                func.count(
                    Coureur.id
                )
            )
            .filter(
                Coureur.course_id
                == COURSE_ID,

                Coureur.statut
                == STATUT_PRET,

                Coureur.heure_depart
                > maintenant,
            )
            .scalar()
            or 0
        )


        # ------------------------------------------
        # COUREURS ENCORE EN COURSE
        # ------------------------------------------
        # Coureurs dont le départ est passé et qui n'ont pas encore terminé.
        coureurs_en_course = (
            session.query(Coureur)
            .filter(
                Coureur.course_id
                == COURSE_ID,

                Coureur.statut
                == STATUT_PRET,

                Coureur.heure_depart
                <= maintenant,
            )
            .order_by(
                Coureur.heure_depart.asc()
            )
            .all()
        )


        # ------------------------------------------
        # ARRIVEES
        # ------------------------------------------

        # Arrivées classées = coureurs ayant le statut arrivé.
        arrivees_classees = (
            session.query(
                func.count(
                    Coureur.id
                )
            )
            .filter(
                Coureur.course_id
                == COURSE_ID,

                Coureur.statut
                == STATUT_ARRIVE,
            )
            .scalar()
            or 0
        )


        # Arrivées à attribuer
        arrivees_en_attente = (
            session.query(
                func.count(
                    Arrivee.id
                )
            )
            .filter(
                Arrivee.course_id
                == COURSE_ID,

                Arrivee.dossard_coureur
                .is_(None),
            )
            .scalar()
            or 0
        )


        arrivees_enregistrees = (
            session.query(
                func.count(
                    Arrivee.id
                )
            )
            .filter(
                Arrivee.course_id
                == COURSE_ID
            )
            .scalar()
            or 0
        )


        # Récapitulatif des statuts enregistrés en base.
        statuts_db = (
            session.query(
                Coureur.statut,
                func.count(
                    Coureur.id
                )
            )
            .filter(
                Coureur.course_id
                == COURSE_ID,

                Coureur.statut.in_(STATUTS),
            )
            .group_by(
                Coureur.statut
            )
            .all()
        )


        statuts = {
            statut: 0
            for statut in STATUTS
        }


        for statut, nombre in statuts_db:

            statuts[statut] = nombre


        derniere_arrivee = (
            session.query(
                func.max(
                    Arrivee.timestamp
                )
            )
            .filter(
                Arrivee.course_id
                == COURSE_ID
            )
            .scalar()
        )


        # ------------------------------------------
        # PROGRESSION
        # ------------------------------------------

        if departs_configures > 0:

            progression = round(
                (
                    arrivees_classees
                    / departs_configures
                ) * 100,
                1
            )

            progression = min(
                progression,
                100.0
            )

        else:

            progression = 0.0


        # ------------------------------------------
        # REPONSE
        # ------------------------------------------

        return {

            "database": True,

            "course": {
                "nom": course.nom,

                "lieu": course.lieu,

                "date": (
                    course.date.strftime(
                        "%d/%m/%Y"
                    )
                    if course.date
                    else None
                ),
            },

            "course_stats": {

                "total_coureurs":
                    total_coureurs,

                "departs_configures":
                    departs_configures,

                "coureurs_prets":
                    coureurs_prets,

                "statuts":
                    statuts,

                "coureurs_en_course": [

                    {
                        "dossard":
                            coureur.dossard,

                        "nom":
                            coureur.nom,

                        "prenom":
                            coureur.prenom,

                        "heure_depart": (

                            coureur.heure_depart
                            .strftime("%H:%M:%S")

                            if coureur.heure_depart

                            else "-"
                        ),
                    }

                    for coureur
                    in coureurs_en_course

                ],

                "arrivees_enregistrees":
                    arrivees_enregistrees,

                "arrivees_classees":
                    arrivees_classees,

                "arrivees_en_attente":
                    arrivees_en_attente,

                "progression":
                    progression,
            },

            "derniere_arrivee": (

                derniere_arrivee
                .strftime("%H:%M:%S.%f")[:-4]

                if derniere_arrivee

                else None
            ),

            "systeme": {

                "serveur_public":
                    verifier_serveur_public(),

                "sse_clients":
                    len(sse_clients),

                "uptime":
                    formater_duree(
                        monotonic()
                        - DEBUT_APPLICATION
                    ),
            },

            "horodatage":
                datetime.now()
                .strftime("%H:%M:%S"),
        }


    except Exception as erreur:

        return {

            "database": False,

            "erreur":
                str(erreur),

            "systeme": {

                "serveur_public":
                    False,

                "sse_clients":
                    len(sse_clients),

                "uptime":
                    formater_duree(
                        monotonic()
                        - DEBUT_APPLICATION
                    ),
            },
        }


    finally:

        session.close()


@dashboard_bp.route(
    "/dashboard"
)
def dashboard():

    etat = (
        construire_etat_dashboard()
    )

    return render_template(
        "dashboard.html",
        course=etat.get(
            "course"
        ),
    )


@dashboard_bp.route(
    "/dashboard/data"
)
def dashboard_data():

    return jsonify(
        construire_etat_dashboard()
    )