#-----------
# APPLICATION CHRONOLIVE
#-----------
# Point d'entrée principal de ChronoLive.
#
# Gestion :
# - création de l'application Flask
# - enregistrement des modules
# - protection des routes publiques et privées
# - initialisation de la base de données
# - création de la course
# - lancement des serveurs
#-----------

import threading
import time

from flask import Flask, request
from werkzeug.serving import make_server
import logging

from config import (
    COURSE,
    PORT_PRIVE,
    PORT_PUBLIC,
    URL_CLASSEMENT_PUBLIC,
)
from database import Session, initialiser_base
from models import Course

from modules.inscription import inscription_bp
from modules.chronometrage import chronometrage_bp
from modules.classement_live import classement_live_bp
from modules.resultats import resultats_bp
from modules.dashboard import dashboard_bp
from debug.database import debug_database_bp  # Debug

app = Flask(__name__)

# Enregistrement des différents modules de ChronoLive.
app.register_blueprint(inscription_bp)
app.register_blueprint(chronometrage_bp)
app.register_blueprint(classement_live_bp)
app.register_blueprint(resultats_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(debug_database_bp)     # Debug


# Masque les requêtes réussies du dashboard,
# mais conserve les erreurs dans le terminal.
class FiltreDashboard(logging.Filter):

    def filter(
        self,
        record
    ):
        if "/dashboard/data" in record.getMessage():

            try:
                status_code = int(
                    record.args[1]
                )

                if status_code < 400:
                    return False

            except (
                IndexError,
                TypeError,
                ValueError
            ):
                pass

        return True


logging.getLogger(
    "werkzeug"
).addFilter(
    FiltreDashboard()
)


#-----------
# PROTECTION DES ROUTES
#-----------
# Les routes du classement live sont accessibles
# depuis le port public.
#
# Les autres routes sont accessibles uniquement
# depuis le port privé du PC de course.
#-----------

ENDPOINTS_PUBLICS = {
    "classement_live.classement_live",
    "classement_live.classement_live_stream",
}


@app.before_request
def proteger_routes_privees():
    # Bloque l'accès aux routes privées depuis le port public.
    endpoint = request.endpoint

    if endpoint in ENDPOINTS_PUBLICS:
        return

    try:
        port = int(
            request.environ.get(
                "SERVER_PORT",
                0
            )
        )
    except (TypeError, ValueError):
        port = 0

    if port != PORT_PRIVE:
        return (
            "Accès interdit.<br><br>"
            "Cette page est réservée au PC de course.",
            403,
        )





#-----------
# INITIALISATION
#-----------

def initialiser_course():
    # Crée la course configurée si elle n'existe pas encore.

    session = Session()

    try:
        course = (
            session.query(Course)
            .filter_by(id=1)
            .first()
        )

        if course is None:
            course = Course(
                id=1,
                nom=COURSE.nom,
                date=COURSE.date,
                lieu=COURSE.lieu,
            )

            session.add(course)
            session.commit()

    finally:
        session.close()


#-----------
# SERVEUR
#-----------

def lancer_serveur(host, port):
    # Lance un serveur Flask multithreadé.

    serveur = make_server(
        host,
        port,
        app,
        threaded=True,
    )

    serveur.serve_forever()


#-----------
# DÉMARRAGE DE CHRONOLIVE
#-----------

if __name__ == "__main__":

    # Initialise les tables de la base.
    initialiser_base()

    # Initialise la course si nécessaire.
    initialiser_course()

    # Serveur privé :
    # inscription, chronométrage et résultats.
    serveur_prive = threading.Thread(
        target=lancer_serveur,
        args=("127.0.0.1", PORT_PRIVE),
        daemon=True,
    )

    # Serveur public :
    # classement live uniquement.
    serveur_public = threading.Thread(
        target=lancer_serveur,
        args=("0.0.0.0", PORT_PUBLIC),
        daemon=True,
    )

    serveur_prive.start()
    serveur_public.start()

    print("============================================================")
    print("                    CHRONOLIVE DÉMARRÉ")
    print("============================================================")
    print()
    print("  FENÊTRES À OUVRIR SUR LE PC DE COURSE")
    print()
    print(f"  [1] TABLEAU DE BORD")
    print(f"      http://127.0.0.1:{PORT_PRIVE}/dashboard")
    print()
    print(f"  [2] INSCRIPTIONS")
    print(f"      http://127.0.0.1:{PORT_PRIVE}/inscription")
    print()
    print(f"  [3] CHRONOMÉTRAGE")
    print(f"      http://127.0.0.1:{PORT_PRIVE}/chronometrage")
    print()
    print(f"  [4] RÉSULTATS / EXPORTS")
    print(f"      http://127.0.0.1:{PORT_PRIVE}/resultats")
    print()
    print("------------------------------------------------------------")
    print("  CLASSEMENT LIVE")
    print()
    print(f"  [5] SUR LE PC DE COURSE")
    print(f"      http://127.0.0.1:{PORT_PRIVE}/classement_live")
    print()
    print("  [6] ACCÈS PUBLIC")
    print(f"      {URL_CLASSEMENT_PUBLIC}")
    print()
    print("------------------------------------------------------------")
    print("  ACCÈS INTERNET")
    print()
    print(f"  Commande Tailscale : tailscale funnel {PORT_PUBLIC}")
    print()
    print("  Les serveurs privé et public sont actifs.")
    print("============================================================")
    print()

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nArrêt de ChronoLive.")

