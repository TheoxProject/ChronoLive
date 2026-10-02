#-----------
# MODULE 3 - CLASSEMENT LIVE
#-----------
# Gestion du classement public en temps réel.
#
# Fonctionnalités :
# - construction du classement
# - affichage de la page publique
# - mise à jour en temps réel avec SSE
# - notification des clients connectés
#
# Une base SQLite correspond à UNE seule course.
#
# Routes :
# - /classement_live
# - /classement_live/stream
#-----------

import json
import queue
import threading

from flask import (
    Blueprint,
    Response,
    render_template,
    stream_with_context,
)

from config import CATEGORIES, CATEGORIES_FFC, STATUT_ARRIVE
from database import Session
from models import Course, Coureur
from utils.temps import formater_temps


classement_live_bp = Blueprint(
    "classement_live",
    __name__
)


# Clients actuellement connectés au flux SSE.
sse_clients = set()

sse_lock = threading.Lock()


def construire_classement(session):
    # Construit le classement à partir des temps enregistrés.

    # Seuls les coureurs officiellement arrivés
    # sont transmis au classement public.
    coureurs = (
        session.query(Coureur)
        .filter(
            Coureur.statut == STATUT_ARRIVE,
        )
        .order_by(
            Coureur.temps_centisecondes.asc()
        )
        .all()
    )

    classement = []

    if not coureurs:
        return classement

    meilleur_temps = (
        coureurs[0].temps_centisecondes
    )

    for position, coureur in enumerate(
        coureurs,
        start=1
    ):
        classement.append({
            "position": position,
            "dossard": coureur.dossard,
            "nom": coureur.nom,
            "prenom": coureur.prenom,
            "categorie": coureur.categorie,
            "categorie_ffc": (
                coureur.categorie_ffc
                or "-"
            ),
            "sexe": coureur.sexe,
            "temps": formater_temps(
                coureur.temps_centisecondes
            ),
            "temps_centisecondes": (
                coureur.temps_centisecondes
            ),
            "ecart": formater_temps(
                coureur.temps_centisecondes
                - meilleur_temps
            ),
        })

    return classement


def notifier_classement():
    # Envoie le nouveau classement
    # à tous les clients SSE connectés.

    session = Session()

    try:
        classement = construire_classement(
            session
        )
    finally:
        session.close()

    with sse_lock:
        for client_queue in list(sse_clients):
            client_queue.put(classement)


@classement_live_bp.route(
    "/classement_live"
)
def classement_live():
    # Affiche la page publique du classement.

    session = Session()

    try:
        course = (
            session.query(Course)
            .first()
        )

        classement = construire_classement(
            session
        )

        return render_template(
            "classement_live.html",
            classement=classement,
            categories=CATEGORIES,
            categories_ffc=CATEGORIES_FFC,
            course_nom=course.nom,
            course_lieu=course.lieu,
            course_date=course.date,
        )

    finally:
        session.close()


@classement_live_bp.route(
    "/classement_live/stream"
)
def classement_live_stream():
    # Ouvre une connexion SSE permanente
    # pour recevoir les mises à jour du classement.

    client_queue = queue.Queue()

    with sse_lock:
        sse_clients.add(client_queue)

    @stream_with_context
    def generate():

        try:
            # Envoie le classement actuel dès la connexion.
            session = Session()

            try:
                classement = construire_classement(
                    session
                )
            finally:
                session.close()

            yield (
                f"data: {json.dumps(classement)}\n\n"
            )

            while True:
                try:
                    # Attend une nouvelle mise à jour.
                    classement = client_queue.get(
                        timeout=20
                    )

                    yield (
                        f"data: {json.dumps(classement)}\n\n"
                    )

                except queue.Empty:
                    # Maintient la connexion active.
                    yield ": heartbeat\n\n"

        finally:
            # Retire le client lorsqu'il se déconnecte.
            with sse_lock:
                sse_clients.discard(client_queue)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )