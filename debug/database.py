#-----------
# MODULE - DEBUG DATABASE
#-----------
# Page de debug dédiée à l'inspection de la base SQLite.
#
# Ce module est indépendant du reste de ChronoLive.
# Il est prévu pour le développement et le débogage.
#
# Fonctionnalités :
# - affichage des courses
# - affichage des coureurs
# - affichage des arrivées
# - affichage des valeurs réellement enregistrées en base
#
# La page est uniquement accessible sur le serveur privé.
#-----------

from flask import (
    Blueprint,
    abort,
    render_template,
    request,
)

from config import PORT_PRIVE, STATUTS
from database import Session
from models import Arrivee, Course, Coureur


debug_database_bp = Blueprint(
    "debug_database",
    __name__,
    url_prefix="/debug/database",
    template_folder="templates",
)


def verifier_acces_prive():
    # Le module de debug ne doit pas être exposé par le serveur public.
    port = request.environ.get("SERVER_PORT")

    if port != str(PORT_PRIVE):
        abort(404)


def formater_valeur(valeur):
    # Formate les valeurs pour l'affichage dans le tableau.
    if valeur is None:
        return "NULL"

    if hasattr(valeur, "strftime"):
        if hasattr(valeur, "hour"):
            return valeur.strftime("%Y-%m-%d %H:%M:%S")

        return valeur.strftime("%d/%m/%Y")

    return str(valeur)


@debug_database_bp.route("/")
def database():
    verifier_acces_prive()

    session = Session()

    try:
        courses = (
            session.query(Course)
            .order_by(Course.id.asc())
            .all()
        )

        coureurs = (
            session.query(Coureur)
            .order_by(Coureur.id.asc())
            .all()
        )

        arrivees = (
            session.query(Arrivee)
            .order_by(Arrivee.id.desc())
            .all()
        )

        return render_template(
            "database.html",
            courses=courses,
            coureurs=coureurs,
            arrivees=arrivees,
            statuts=STATUTS,
            formater_valeur=formater_valeur,
        )

    finally:
        session.close()
