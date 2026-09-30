# ------------------------------------------------------------
# APPLICATION CHRONOLIVE
# ------------------------------------------------------------
# Point d'entrée principal de ChronoLive.
#
# Gestion :
# - création de l'application Flask
# - enregistrement des modules
# - protection des routes publiques et privées
# - gestion des courses
# - sélection d'une base au démarrage
# - lancement des serveurs
#
# Une seule course est utilisée par lancement du logiciel.
# Pour changer de course, ChronoLive doit être fermé puis relancé.
# ------------------------------------------------------------

import logging
import threading
import time

from datetime import datetime
from datetime import time as datetime_time

from flask import (
    Flask,
    redirect,
    render_template,
    request,
    url_for,
)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from werkzeug.serving import make_server

from config import (
    PORT_PRIVE,
    PORT_PUBLIC,
    URL_CLASSEMENT_PUBLIC,
    TYPES_COURSE,
    TYPE_GRIMPEE,
    TYPE_CRITERIUM,
)

from database import (
    Session,
    base_est_initialisee,
    construire_url_sqlite,
    creer_base_course,
    initialiser_base,
    lister_courses,
)

from models import Course, Coureur

from modules.inscription import inscription_bp
from modules.chronometrage import chronometrage_bp
from modules.classement_live import classement_live_bp
from modules.resultats import resultats_bp
from modules.dashboard import dashboard_bp

from debug.database import debug_database_bp


# ------------------------------------------------------------
# APPLICATION FLASK
# ------------------------------------------------------------

app = Flask(__name__)


# ------------------------------------------------------------
# ENREGISTREMENT DES MODULES
# ------------------------------------------------------------

app.register_blueprint(inscription_bp)
app.register_blueprint(chronometrage_bp)
app.register_blueprint(classement_live_bp)
app.register_blueprint(resultats_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(debug_database_bp)


# ------------------------------------------------------------
# FILTRE TERMINAL DASHBOARD
# ------------------------------------------------------------
# Masque les requêtes réussies de /dashboard/data
# mais conserve les erreurs pour le débogage.
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# ROUTES PUBLIQUES
# ------------------------------------------------------------

ENDPOINTS_PUBLICS = {
    "classement_live.classement_live",
    "classement_live.classement_live_stream",
}


# ------------------------------------------------------------
# ROUTES DE GESTION DES COURSES
# ------------------------------------------------------------

ENDPOINTS_GESTION_COURSES = {
    "accueil",
    "charger_course",
    "nouvelle_course",
    "creer_course",
    "modifier_course",
    "enregistrer_modification_course",
}


# ------------------------------------------------------------
# PROTECTION DES ROUTES
# ------------------------------------------------------------

@app.before_request
def proteger_routes():

    endpoint = request.endpoint

    # --------------------------------------------------------
    # ROUTES PUBLIQUES
    # --------------------------------------------------------

    if endpoint in ENDPOINTS_PUBLICS:

        if not base_est_initialisee():

            return (
                "Aucune course n'est actuellement chargée.",
                503,
            )

        return

    # --------------------------------------------------------
    # PORT UTILISÉ
    # --------------------------------------------------------

    try:

        port = int(
            request.environ.get(
                "SERVER_PORT",
                0
            )
        )

    except (
        TypeError,
        ValueError
    ):

        port = 0

    # --------------------------------------------------------
    # TOUT LE RESTE EST PRIVÉ
    # --------------------------------------------------------

    if port != PORT_PRIVE:

        return (
            "Accès interdit.<br><br>"
            "Cette page est réservée au PC de course.",
            403,
        )

    # --------------------------------------------------------
    # UNE DB EST DÉJÀ CHARGÉE
    # --------------------------------------------------------
    # Aucun changement de course pendant l'exécution.
    # Pour changer de course :
    # fermer ChronoLive puis le relancer.
    # --------------------------------------------------------

    if base_est_initialisee():

        if endpoint in ENDPOINTS_GESTION_COURSES:

            return redirect(
                url_for(
                    "dashboard.dashboard"
                )
            )

        return

    # --------------------------------------------------------
    # AUCUNE DB N'EST CHARGÉE
    # --------------------------------------------------------

    if endpoint not in ENDPOINTS_GESTION_COURSES:

        return redirect(
            url_for(
                "accueil"
            )
        )


# ------------------------------------------------------------
# OUTIL : RECHERCHE D'UNE COURSE
# ------------------------------------------------------------

def trouver_course(
    nom_fichier
):
    """
    Recherche une course à partir du nom de son fichier DB.
    """

    for course in lister_courses():

        if course["fichier"].name == nom_fichier:

            return course

    return None


# ------------------------------------------------------------
# PAGE D'ACCUEIL
# ------------------------------------------------------------

@app.route("/")
def accueil():

    if base_est_initialisee():

        return redirect(
            url_for(
                "dashboard.dashboard"
            )
        )

    courses = lister_courses()

    return render_template(
        "courses.html",
        courses=courses,
    )


# ------------------------------------------------------------
# CHARGER UNE COURSE
# ------------------------------------------------------------

@app.route(
    "/charger_course/<path:nom_fichier>"
)
def charger_course(
    nom_fichier
):

    if base_est_initialisee():

        return redirect(
            url_for(
                "dashboard.dashboard"
            )
        )

    course = trouver_course(
        nom_fichier
    )

    if course is None:

        return (
            "Course introuvable.",
            404,
        )

    initialiser_base(
        course["fichier"]
    )

    return redirect(
        url_for(
            "dashboard.dashboard"
        )
    )


# ------------------------------------------------------------
# NOUVELLE COURSE - FORMULAIRE
# ------------------------------------------------------------

@app.route(
    "/nouvelle_course"
)
def nouvelle_course():

    if base_est_initialisee():

        return redirect(
            url_for(
                "dashboard.dashboard"
            )
        )

    return render_template(
        "nouvelle_course.html",
        types_course=TYPES_COURSE,
    )


# ------------------------------------------------------------
# NOUVELLE COURSE - CREATION
# ------------------------------------------------------------

@app.route(
    "/nouvelle_course",
    methods=["POST"]
)
def creer_course():

    if base_est_initialisee():

        return redirect(
            url_for(
                "dashboard.dashboard"
            )
        )

    nom = request.form.get(
        "nom",
        ""
    ).strip()

    lieu = request.form.get(
        "lieu",
        ""
    ).strip()

    date_str = request.form.get(
        "date",
        ""
    ).strip()

    type_course = request.form.get(
        "type_course",
        ""
    ).strip()

    heure_depart_str = request.form.get(
        "heure_depart",
        ""
    ).strip()

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if not nom:

        return (
            "Le nom de la course est obligatoire.",
            400,
        )

    if not date_str:

        return (
            "La date de la course est obligatoire.",
            400,
        )

    if type_course not in TYPES_COURSE:

        return (
            "Type de course invalide.",
            400,
        )

    try:

        date_course = datetime.strptime(
            date_str,
            "%Y-%m-%d"
        ).date()

    except ValueError:

        return (
            "Date invalide.",
            400,
        )

    heure_depart = None

    if heure_depart_str:

        try:

            heure_depart = datetime.strptime(
                heure_depart_str,
                "%H:%M"
            ).time()

        except ValueError:

            return (
                "Heure de départ invalide.",
                400,
            )

    # --------------------------------------------------------
    # CREATION DE LA DB
    # --------------------------------------------------------

    chemin = creer_base_course(
        nom=nom,
        date_course=date_course,
        lieu=lieu,
        type_course=type_course,
        heure_depart=heure_depart,
    )

    # --------------------------------------------------------
    # LA NOUVELLE COURSE EST DIRECTEMENT CHARGEE
    # --------------------------------------------------------

    initialiser_base(
        chemin
    )

    return redirect(
        url_for(
            "dashboard.dashboard"
        )
    )


# ------------------------------------------------------------
# MODIFIER UNE COURSE
# ------------------------------------------------------------
# Le type de course n'est volontairement PAS modifiable.
# Il est défini lors de la création et reste inchangé.
# ------------------------------------------------------------

@app.route(
    "/modifier_course/<path:nom_fichier>"
)
def modifier_course(
    nom_fichier
):

    if base_est_initialisee():

        return redirect(
            url_for(
                "dashboard.dashboard"
            )
        )

    course = trouver_course(
        nom_fichier
    )

    if course is None:

        return (
            "Course introuvable.",
            404,
        )

    return render_template(
        "modifier_course.html",
        course=course,
    )


# ------------------------------------------------------------
# CALCUL DU DECALAGE D'UNE HEURE
# ------------------------------------------------------------

def calculer_decalage_secondes(
    ancienne_heure,
    nouvelle_heure
):
    """
    Retourne le décalage en secondes entre deux heures.
    """

    ancienne_secondes = (
        ancienne_heure.hour * 3600
        + ancienne_heure.minute * 60
        + ancienne_heure.second
        + ancienne_heure.microsecond / 1_000_000
    )

    nouvelle_secondes = (
        nouvelle_heure.hour * 3600
        + nouvelle_heure.minute * 60
        + nouvelle_heure.second
        + nouvelle_heure.microsecond / 1_000_000
    )

    return nouvelle_secondes - ancienne_secondes


def appliquer_decalage_depart(
    heure_depart,
    decalage_secondes
):
    """
    Applique un décalage à une heure.
    """

    secondes = (
        heure_depart.hour * 3600
        + heure_depart.minute * 60
        + heure_depart.second
        + heure_depart.microsecond / 1_000_000
    )

    secondes = (
        secondes + decalage_secondes
    ) % 86400

    heures = int(
        secondes // 3600
    )

    secondes_restantes = (
        secondes % 3600
    )

    minutes = int(
        secondes_restantes // 60
    )

    secondes_restantes %= 60

    secondes_entieres = int(
        secondes_restantes
    )

    microsecondes = int(
        round(
            (
                secondes_restantes
                - secondes_entieres
            ) * 1_000_000
        )
    )

    if microsecondes >= 1_000_000:

        secondes_entieres += 1
        microsecondes -= 1_000_000

    if secondes_entieres >= 60:

        minutes += 1
        secondes_entieres -= 60

    if minutes >= 60:

        heures += 1
        minutes -= 60

    heures %= 24

    return datetime_time(
        heures,
        minutes,
        secondes_entieres,
        microsecondes,
    )


# ------------------------------------------------------------
# ENREGISTRER LA MODIFICATION
# ------------------------------------------------------------

@app.route(
    "/modifier_course/<path:nom_fichier>",
    methods=["POST"]
)
def enregistrer_modification_course(
    nom_fichier
):

    if base_est_initialisee():

        return redirect(
            url_for(
                "dashboard.dashboard"
            )
        )

    course_info = trouver_course(
        nom_fichier
    )

    if course_info is None:

        return (
            "Course introuvable.",
            404,
        )

    chemin = course_info["fichier"]

    nom = request.form.get(
        "nom",
        ""
    ).strip()

    lieu = request.form.get(
        "lieu",
        ""
    ).strip()

    date_str = request.form.get(
        "date",
        ""
    ).strip()

    heure_depart_str = request.form.get(
        "heure_depart",
        ""
    ).strip()

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if not nom:

        return (
            "Le nom de la course est obligatoire.",
            400,
        )

    if not date_str:

        return (
            "La date de la course est obligatoire.",
            400,
        )

    try:

        date_course = datetime.strptime(
            date_str,
            "%Y-%m-%d"
        ).date()

    except ValueError:

        return (
            "Date invalide.",
            400,
        )

    heure_depart = None

    if heure_depart_str:

        try:

            heure_depart = datetime.strptime(
                heure_depart_str,
                "%H:%M"
            ).time()

        except ValueError:

            return (
                "Heure de départ invalide.",
                400,
            )

    # --------------------------------------------------------
    # OUVERTURE TEMPORAIRE DE LA DB
    # --------------------------------------------------------

    temp_engine = create_engine(
        construire_url_sqlite(
            chemin
        ),
        connect_args={
            "check_same_thread": False
        }
    )

    TempSession = sessionmaker(
        bind=temp_engine
    )

    session = TempSession()

    try:

        course = (
            session.query(
                Course
            )
            .first()
        )

        if course is None:

            return (
                "Course invalide.",
                400,
            )

        # ----------------------------------------------------
        # ANCIENNE HEURE DE DEPART
        # ----------------------------------------------------

        ancienne_heure_depart = (
            course.heure_depart
        )

        # ----------------------------------------------------
        # MODIFICATION DES INFORMATIONS
        # ----------------------------------------------------
        # Le type de course n'est pas modifié.
        # Il reste celui défini lors de la création.
        # ----------------------------------------------------

        course.nom = nom
        course.date = date_course
        course.lieu = lieu
        course.heure_depart = heure_depart

        # ----------------------------------------------------
        # DEPART COMMUN
        # ----------------------------------------------------
        # Pour une Grimpée ou un Critérium, une modification
        # de l'heure de départ décale tous les départs coureurs.
        #
        # Pour un CLM, les heures individuelles restent
        # inchangées.
        # ----------------------------------------------------

        if (
            course.type_course
            in {
                TYPE_GRIMPEE,
                TYPE_CRITERIUM,
            }

            and ancienne_heure_depart is not None

            and heure_depart is not None

            and ancienne_heure_depart
            != heure_depart
        ):

            decalage_secondes = (
                calculer_decalage_secondes(
                    ancienne_heure_depart,
                    heure_depart,
                )
            )

            coureurs = (
                session.query(
                    Coureur
                )
                .all()
            )

            for coureur in coureurs:

                if coureur.heure_depart is None:
                    continue

                coureur.heure_depart = (
                    appliquer_decalage_depart(
                        coureur.heure_depart,
                        decalage_secondes,
                    )
                )

        session.commit()

    except Exception:

        session.rollback()
        raise

    finally:

        session.close()
        temp_engine.dispose()

    return redirect(
        url_for(
            "accueil"
        )
    )


# ------------------------------------------------------------
# SERVEUR
# ------------------------------------------------------------

def lancer_serveur(
    host,
    port
):

    serveur = make_server(
        host,
        port,
        app,
        threaded=True,
    )

    serveur.serve_forever()


# ------------------------------------------------------------
# DEMARRAGE
# ------------------------------------------------------------

if __name__ == "__main__":

    serveur_prive = threading.Thread(
        target=lancer_serveur,
        args=(
            "127.0.0.1",
            PORT_PRIVE,
        ),
        daemon=True,
    )

    serveur_public = threading.Thread(
        target=lancer_serveur,
        args=(
            "0.0.0.0",
            PORT_PUBLIC,
        ),
        daemon=True,
    )

    serveur_prive.start()
    serveur_public.start()

    print(
        "============================================================"
    )

    print(
        "                    CHRONOLIVE DÉMARRÉ"
    )

    print(
        "============================================================"
    )

    print()

    print(
        "  GESTION DES COURSES"
    )

    print(
        f"      http://127.0.0.1:{PORT_PRIVE}/"
    )

    print()

    print(
        "  Choisissez ou créez une course."
    )

    print(
        "  Une seule course peut être utilisée par lancement."
    )

    print(
        "  Pour changer de course : fermer puis relancer ChronoLive."
    )

    print()

    print(
        "------------------------------------------------------------"
    )

    print(
        "  CLASSEMENT LIVE PUBLIC"
    )

    print()

    print(
        f"      {URL_CLASSEMENT_PUBLIC}"
    )

    print()

    print(
        f"  Commande Tailscale : tailscale funnel {PORT_PUBLIC}"
    )

    print()

    print(
        "  Les serveurs privé et public sont actifs."
    )

    print(
        "============================================================"
    )

    print()

    try:

        while True:

            time.sleep(
                1
            )

    except KeyboardInterrupt:

        print(
            "\nArrêt de ChronoLive."
        )


