from datetime import datetime, date
import time
import json
import queue
import threading
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED

from flask import Flask, render_template, request, redirect, url_for, Response, stream_with_context, send_file

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from werkzeug.serving import make_server

from models import Base, Course, Coureur, Arrivee
from resultats import construire_resultat
from config import COURSE, CATEGORIES, CATEGORIES_FFC, URL_CLASSEMENT_PUBLIC, PORT_PRIVE, PORT_PUBLIC, DATABASE_URL
from exports.pdf import exporter_pdf
from exports.png import exporter_png
from exports.excel import exporter_excel
from exports.csv import exporter_csv

app = Flask(__name__)

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False
    }
)

Session = sessionmaker(bind=engine)

COURSE_ID = 1


# ============================================================
# SSE
# ============================================================

sse_clients = set()
sse_clients_lock = threading.Lock()

ENDPOINTS_PUBLICS = {
    "classement_live",
    "classement_live_stream"
}

# gestion des redirections
@app.before_request
def proteger_routes_privees():

    endpoint = request.endpoint

    if endpoint is None:
        return None

    port = request.environ.get(
        "SERVER_PORT"
    )

    port = int(port)

    if endpoint in ENDPOINTS_PUBLICS:
        return None

    if port != PORT_PRIVE:

        return (
            "Accès interdit. "
            "Cette page est réservée "
            "au PC de course.",
            403
        )

    return None


# ============================================================
# OUTILS
# ============================================================

def calculer_temps_centisecondes(
    heure_depart,
    timestamp_arrivee
):
    """
    Calcule le temps de course en centisecondes.

    Le calcul utilise uniquement l'heure de la journée.
    La date n'est volontairement pas prise en compte.
    """

    if heure_depart is None:
        return None

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
    )

    temps_secondes = (
        arrivee_secondes
        - depart_secondes
    )

    return max(
        0,
        round(temps_secondes * 100)
    )


def formater_temps(total_centisecondes):
    """
    Transforme un temps en centisecondes
    en format HH:MM:SS.CC
    """

    if total_centisecondes is None:
        return "-"

    heures = (
        total_centisecondes
        // 360000
    )

    minutes = (
        total_centisecondes
        // 6000
    ) % 60

    secondes = (
        total_centisecondes
        // 100
    ) % 60

    centiemes = (
        total_centisecondes
        % 100
    )

    return (
        f"{heures:02d}:"
        f"{minutes:02d}:"
        f"{secondes:02d}."
        f"{centiemes:02d}"
    )


# ============================================================
# MODULE 1 — INSCRIPTIONS
# ============================================================

@app.route("/")
def inscription():

    with Session() as session:

        course = session.get(
            Course,
            COURSE_ID
        )

        coureurs = (
            session.query(Coureur)
            .filter(
                Coureur.course_id == COURSE_ID
            )
            .order_by(
                Coureur.nom.asc(),
                Coureur.prenom.asc()
            )
            .all()
        )

        return render_template(
            "inscription.html",
            course_nom=course.nom,
            course_date=course.date,
            course_lieu=course.lieu,
            coureurs=coureurs,
            categories=CATEGORIES,
            categories_ffc=CATEGORIES_FFC
        )



# ============================================================
# MODULE 1 — INSCRIPTION
# ============================================================


@app.route(
    "/ajouter_coureur",
    methods=["POST"]
)
def ajouter_coureur():

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

    licence = request.form.get(
        "licence",
        ""
    ).strip()

    club = request.form.get(
        "club",
        ""
    ).strip()

    categorie = request.form.get(
        "categorie",
        ""
    ).strip()

    categorie_ffc = request.form.get(
        "categorie_ffc",
        ""
    ).strip()

    if categorie not in CATEGORIES:
        return redirect(
            url_for("inscription")
        )

    if categorie_ffc and categorie_ffc not in CATEGORIES_FFC : # possiblité de laisser le champ vide
        return redirect(
            url_for("inscription")
        )

    if not date_naissance_str:
        return redirect(
            url_for("inscription")
        )

    date_naissance = datetime.strptime(
        date_naissance_str,
        "%Y-%m-%d"
    ).date()

    with Session() as session:

        coureur = Coureur(
            nom=nom,
            prenom=prenom,
            sexe=sexe,
            date_naissance=date_naissance,
            licence=licence or None,
            club=club or None,
            categorie=categorie,
            categorie_ffc=categorie_ffc or None,
            course_id=COURSE_ID
        )

        session.add(coureur)
        session.commit()


    return redirect(
        url_for("inscription")
    )


@app.route(
    "/modifier_coureur/<int:coureur_id>",
    methods=["POST"]
)
def modifier_coureur(coureur_id):

    with Session() as session:

        coureur = session.get(
            Coureur,
            coureur_id
        )

        if coureur is None:
            return redirect(
                url_for("inscription")
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

        date_naissance_str = request.form.get(
            "date_naissance",
            ""
        ).strip()

        if date_naissance_str:

            coureur.date_naissance = (
                datetime.strptime(
                    date_naissance_str,
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

        categorie = request.form.get(
            "categorie",
            ""
        ).strip()

        if categorie in CATEGORIES:
            coureur.categorie = categorie

        categorie_ffc = request.form.get(
            "categorie_ffc",
            ""
        ).strip()

        if (
            categorie_ffc
            and categorie_ffc not in CATEGORIES_FFC
        ):
            return redirect(
                url_for("inscription")
            )

        coureur.categorie_ffc = (
            categorie_ffc or None
        )

        dossard_str = request.form.get(
            "dossard",
            ""
        ).strip()

        if dossard_str:

            try:
                coureur.dossard = int(
                    dossard_str
                )
            except ValueError:
                coureur.dossard = None

        else:

            coureur.dossard = None

        heure_depart_str = request.form.get(
            "heure_depart",
            ""
        ).strip()

        if heure_depart_str:

            for format_heure in (
                "%H:%M:%S",
                "%H:%M"
            ):
                try:

                    coureur.heure_depart = (
                        datetime.strptime(
                            heure_depart_str,
                            format_heure
                        ).time()
                    )

                    break

                except ValueError:

                    coureur.heure_depart = None

        else:

            coureur.heure_depart = None

        try:

            session.commit()

        except Exception:

            session.rollback()


    return redirect(
        url_for("inscription")
    )


@app.route(
    "/supprimer_coureur/<int:coureur_id>",
    methods=["POST"]
)
def supprimer_coureur(coureur_id):

    with Session() as session:

        coureur = session.get(
            Coureur,
            coureur_id
        )

        if coureur is None:
            return redirect(
                url_for("inscription")
            )

        if coureur.dossard is not None:

            session.query(
                Arrivee
            ).filter(
                Arrivee.course_id == COURSE_ID,
                Arrivee.dossard_coureur
                == coureur.dossard
            ).delete(
                synchronize_session=False
            )

        session.delete(coureur)
        session.commit()


    return redirect(
        url_for("inscription")
    )


# ============================================================
# MODULE 2 — CHRONOMÉTRAGE
# ============================================================

@app.route("/chronometrage")
def chronometrage():

    erreur = request.args.get(
        "erreur"
    )

    with Session() as session:

        arrivees = (
            session.query(Arrivee)
            .filter(
                Arrivee.course_id == COURSE_ID
            )
            .order_by(
                Arrivee.id.desc()
            )
            .all()
        )

        arrivees_en_attente = []

        arrivees_associees = []

        for arrivee in arrivees:

            if arrivee.dossard_coureur is None:

                arrivees_en_attente.append(
                    arrivee
                )

                continue

            coureur = (
                session.query(Coureur)
                .filter(
                    Coureur.course_id == COURSE_ID,
                    Coureur.dossard
                    == arrivee.dossard_coureur
                )
                .first()
            )

            if coureur is None:

                continue

            arrivees_associees.append(
                {
                    "id": arrivee.id,
                    "dossard": coureur.dossard,
                    "nom": coureur.nom,
                    "prenom": coureur.prenom,
                    "categorie": coureur.categorie,
                    "heure_depart": coureur.heure_depart,
                    "timestamp": arrivee.timestamp,
                    "temps": formater_temps(
                        coureur.temps_centisecondes
                    )
                }
            )

        return render_template(
            "chronometrage.html",
            arrivees_en_attente=arrivees_en_attente,
            arrivees_associees=arrivees_associees,
            erreur=erreur
        )


@app.route(
    "/enregistrer_arrivee",
    methods=["POST"]
)
def enregistrer_arrivee():

    timestamp = datetime.now()

    with Session() as session:

        arrivee = Arrivee(
            timestamp=timestamp,
            dossard_coureur=None,
            course_id=COURSE_ID
        )

        session.add(arrivee)
        session.commit()

    return redirect(
        url_for("chronometrage")
    )


@app.route(
    "/associer_arrivee/<int:arrivee_id>",
    methods=["POST"]
)
def associer_arrivee(arrivee_id):

    dossard_str = request.form.get(
        "dossard",
        ""
    ).strip()

    # Vérification du format du dossard
    if not dossard_str.isdigit():

        return redirect(
            url_for(
                "chronometrage",
                erreur="Dossard invalide."
            )
        )

    dossard = int(
        dossard_str
    )

    with Session() as session:

        # Récupération de l'arrivée
        arrivee = session.get(
            Arrivee,
            arrivee_id
        )

        if arrivee is None:

            return redirect(
                url_for(
                    "chronometrage",
                    erreur="Arrivée introuvable."
                )
            )

        if arrivee.course_id != COURSE_ID:

            return redirect(
                url_for(
                    "chronometrage",
                    erreur="Arrivée invalide."
                )
            )

        # Recherche du coureur
        coureur = (
            session.query(Coureur)
            .filter(
                Coureur.course_id == COURSE_ID,
                Coureur.dossard == dossard
            )
            .first()
        )

        if coureur is None:

            return redirect(
                url_for(
                    "chronometrage",
                    erreur=(
                        f"Le dossard "
                        f"{dossard} "
                        f"n'existe pas."
                    )
                )
            )


        # Vérification : heure de départ renseignée
        if coureur.heure_depart is None:

            return redirect(
                url_for(
                    "chronometrage",
                    erreur=(
                        f"Le coureur portant "
                        f"le dossard {dossard} "
                        f"n'a pas d'heure de départ."
                    )
                )
            )
        
        # VERIFICATION : DOSSARD DEJA UTILISE
        arrivee_existante = (
            session.query(Arrivee)
            .filter(
                Arrivee.course_id == COURSE_ID,
                Arrivee.dossard_coureur == dossard,
                Arrivee.id != arrivee_id
            )
            .first()
        )

        if arrivee_existante is not None:

            return redirect(
                url_for(
                    "chronometrage",
                    erreur=(
                        f"Le dossard "
                        f"{dossard} "
                        f"est déjà associé à une arrivée."
                    )
                )
            )

        # ASSOCIATION
        arrivee.dossard_coureur = dossard

        coureur.heure_arrivee = (
            arrivee.timestamp
        )

        coureur.temps_centisecondes = (
            calculer_temps_centisecondes(
                coureur.heure_depart,
                arrivee.timestamp
            )
        )

        coureur.statut = "arrive"

        session.commit()

    notifier_classement()

    return redirect(
        url_for("chronometrage")
    )


@app.route(
    "/supprimer_arrivee/<int:arrivee_id>",
    methods=["POST"]
)
def supprimer_arrivee(arrivee_id):

    with Session() as session:

        arrivee = session.get(
            Arrivee,
            arrivee_id
        )

        if arrivee is None:

            return redirect(
                url_for("chronometrage")
            )

        dossard = (
            arrivee.dossard_coureur
        )

        if dossard is not None:

            coureur = (
                session.query(Coureur)
                .filter(
                    Coureur.course_id == COURSE_ID,
                    Coureur.dossard == dossard
                )
                .first()
            )

            if coureur is not None:

                coureur.heure_arrivee = None

                coureur.temps_centisecondes = (
                    None
                )

                coureur.statut = "en_course"

        session.delete(arrivee)
        session.commit()

    notifier_classement()

    return redirect(
        url_for("chronometrage")
    )


# ============================================================
# MODULE 3 — CLASSEMENT LIVE
# ============================================================

def construire_classement(session):

    coureurs = (
        session.query(Coureur)
        .filter(
            Coureur.course_id == COURSE_ID,
            Coureur.temps_centisecondes != None
        )
        .order_by(
            Coureur.temps_centisecondes.asc()
        )
        .all()
    )

    if not coureurs:
        return []

    meilleur_temps = (
        coureurs[0].temps_centisecondes
    )

    classement = []

    for position, coureur in enumerate(
        coureurs,
        start=1
    ):

        ecart_centisecondes = (
            coureur.temps_centisecondes
            - meilleur_temps
        )

        if position == 1:

            ecart = "-"

        else:

            ecart = formater_temps(
                ecart_centisecondes
            )

        classement.append(
            {
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
                "ecart": ecart
            }
        )

    return classement


def notifier_classement():

    with Session() as session:

        classement = construire_classement(
            session
        )

    with sse_clients_lock:

        clients = list(
            sse_clients
        )

    for client_queue in clients:

        client_queue.put(
            classement
        )


@app.route(
    f"/classement_live"
)
def classement_live():

    with Session() as session:

        course = session.get(
            Course,
            COURSE_ID
        )

        classement = construire_classement(
            session
        )

        return render_template(
            "classement_live.html",
            classement=classement,
            categories=CATEGORIES,
            course_nom=course.nom,
            course_date=course.date,
            course_lieu=course.lieu
        )


@app.route(
    f"/classement_live/stream"
)
def classement_live_stream():

    client_queue = queue.Queue()

    with sse_clients_lock:

        sse_clients.add(
            client_queue
        )

    def generate():

        try:

            with Session() as session:

                classement = construire_classement(
                    session
                )

            yield (
                "data: "
                + json.dumps(
                    classement,
                    ensure_ascii=False
                )
                + "\n\n"
            )

            while True:

                try:

                    classement = client_queue.get(
                        timeout=20
                    )

                    yield (
                        "data: "
                        + json.dumps(
                            classement,
                            ensure_ascii=False
                        )
                        + "\n\n"
                    )

                except queue.Empty:

                    yield ": heartbeat\n\n"

        except GeneratorExit:

            pass

        finally:

            with sse_clients_lock:

                sse_clients.discard(
                    client_queue
                )

    return Response(
        stream_with_context(
            generate()
        ),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )



# ============================================================
# MODULE 4 — IMPRESSION RESULTATS
# ============================================================

@app.route("/resultats")
def resultats():

    type_classement = request.args.get(
        "type",
        "scratch"
    )

    valeur = request.args.get(
        "valeur"
    )

    with Session() as session:

        course = session.get(
            Course,
            COURSE_ID
        )

        resultat = construire_resultat(
            session,
            type_classement,
            valeur
        )

        if type_classement == "scratch":

            titre_classement = "Classement Scratch"

        elif type_classement == "categorie":

            titre_classement = (
                f"Classement {valeur}"
            )

        elif type_classement == "categorie_ffc":

            titre_classement = (
                f"Classement FFC {valeur}"
            )

        elif type_classement == "sexe":

            titre_classement = (
                "Classement "
                + (
                    "Hommes"
                    if valeur == "M"
                    else "Femmes"
                )
            )

        else:

            titre_classement = "Résultats"

        resultat_apercu = [
            {
                "dossard": coureur["dossard"],
                "nom": coureur["nom"],
                "prenom": coureur["prenom"],
                "temps_centisecondes": coureur["temps_centisecondes"]
            }
            for coureur in resultat
        ]
        
        return render_template(
            "resultats.html",
            resultat=resultat,
            resultat_apercu=resultat_apercu,
            type_classement=type_classement,
            valeur=valeur,
            titre_classement=titre_classement,
            categories=CATEGORIES,
            categories_ffc=CATEGORIES_FFC,
            course_nom=course.nom,
            course_date=course.date,
            course_lieu=course.lieu,
            formater_temps=formater_temps
        )



@app.route(
    "/export_resultats"
)
def export_resultats():

    type_classement = request.args.get(
        "type",
        "scratch"
    )

    valeur = request.args.get(
        "valeur"
    )

    format_export = request.args.get(
        "format",
        "pdf"
    ).lower()


    # ========================================================
    # VERIFICATION DU FORMAT
    # ========================================================

    formats_valides = {
        "pdf",
        "png",
        "excel",
        "csv"
    }


    if format_export not in formats_valides:

        return (
            "Format d'export invalide.",
            400
        )


    # ========================================================
    # VERIFICATION DU TYPE
    # ========================================================

    types_valides = {
        "scratch",
        "categorie",
        "categorie_ffc",
        "sexe"
    }


    if type_classement not in types_valides:

        return (
            "Type de classement invalide.",
            400
        )


    # ========================================================
    # CAS "TOUTES LES CATEGORIES"
    # ========================================================

    export_toutes_categories = (

        (
            type_classement == "categorie"
            and not valeur
        )

        or

        (
            type_classement == "categorie_ffc"
            and not valeur
        )

    )


    # ========================================================
    # EXPORT UNIQUE
    # ========================================================

    if not export_toutes_categories:

        with Session() as session:

            course = session.get(
                Course,
                COURSE_ID
            )

            resultat = construire_resultat(
                session,
                type_classement,
                valeur
            )


        # ====================================================
        # TITRE
        # ====================================================

        if type_classement == "scratch":

            titre_classement = (
                "Classement Scratch"
            )


        elif type_classement == "categorie":

            titre_classement = (
                "Classement "
                + valeur
            )


        elif type_classement == "categorie_ffc":

            titre_classement = (
                "Classement FFC "
                + valeur
            )


        elif type_classement == "sexe":

            if valeur == "M":

                titre_classement = (
                    "Classement Hommes"
                )

            elif valeur == "F":

                titre_classement = (
                    "Classement Femmes"
                )

            else:

                titre_classement = (
                    "Classement Sexe"
                )


        titre = (
            course.nom
            + " - "
            + titre_classement
        )


        # ====================================================
        # CATEGORIE A AFFICHER
        # ====================================================

        for coureur in resultat:

            if type_classement == "scratch":

                categorie = (
                    coureur[
                        "categorie"
                    ]
                    or "-"
                )

                categorie_ffc = (
                    coureur[
                        "categorie_ffc"
                    ]
                    or "-"
                )

                coureur[
                    "categorie_export"
                ] = (
                    categorie
                    + " / "
                    + categorie_ffc
                )


            elif type_classement == "categorie_ffc":

                coureur[
                    "categorie_export"
                ] = (
                    coureur[
                        "categorie_ffc"
                    ]
                    or "-"
                )


            else:

                coureur[
                    "categorie_export"
                ] = (
                    coureur[
                        "categorie"
                    ]
                    or "-"
                )


        # ====================================================
        # EXPORT PDF
        # ====================================================

        if format_export == "pdf":

            contenu = exporter_pdf(
                resultat,
                titre
            )


            return send_file(

                BytesIO(contenu),

                mimetype="application/pdf",

                as_attachment=True,

                download_name=(
                    "resultats.pdf"
                )
            )


        # ====================================================
        # EXPORT PNG
        # ====================================================

        elif format_export == "png":

            contenu = exporter_png(
                resultat,
                titre,
                type_classement
            )


            return send_file(

                BytesIO(contenu),

                mimetype="image/png",

                as_attachment=True,

                download_name=(
                    "resultats.png"
                )
            )


        # ====================================================
        # EXPORT EXCEL
        # ====================================================

        elif format_export == "excel":

            contenu = exporter_excel(
                resultat,
                titre,
                type_classement
            )


            return send_file(

                BytesIO(contenu),

                mimetype=(
                    "application/vnd.openxmlformats-"
                    "officedocument.spreadsheetml.sheet"
                ),

                as_attachment=True,

                download_name=(
                    "resultats.xlsx"
                )
            )


        # ====================================================
        # EXPORT CSV
        # ====================================================

        elif format_export == "csv":

            contenu = exporter_csv(
                resultat,
                type_classement
            )


            return send_file(

                BytesIO(contenu),

                mimetype="text/csv",

                as_attachment=True,

                download_name=(
                    "resultats.csv"
                )
            )


    # ========================================================
    # TOUTES LES CATEGORIES
    # ========================================================

    if type_classement == "categorie":

        categories_a_exporter = (
            CATEGORIES
        )

        mode_ffc = False

        type_export = (
            "categorie"
        )

    else:

        categories_a_exporter = (
            CATEGORIES_FFC
        )

        mode_ffc = True

        type_export = (
            "categorie_ffc"
        )


    # ========================================================
    # CREATION DU ZIP
    # ========================================================

    zip_buffer = BytesIO()


    with ZipFile(
        zip_buffer,
        mode="w",
        compression=ZIP_DEFLATED
    ) as archive:

        with Session() as session:

            course = session.get(
                Course,
                COURSE_ID
            )


            for categorie in categories_a_exporter:

                resultat = construire_resultat(
                    session,
                    type_export,
                    categorie
                )


                # ------------------------------------------------
                # CATEGORIE VIDE
                # ------------------------------------------------

                if not resultat:

                    continue


                # ------------------------------------------------
                # CATEGORIE A AFFICHER
                # ------------------------------------------------

                for coureur in resultat:

                    if mode_ffc:

                        coureur[
                            "categorie_export"
                        ] = (
                            coureur[
                                "categorie_ffc"
                            ]
                            or "-"
                        )

                    else:

                        coureur[
                            "categorie_export"
                        ] = (
                            coureur[
                                "categorie"
                            ]
                            or "-"
                        )


                # ------------------------------------------------
                # TITRE
                # ------------------------------------------------

                if mode_ffc:

                    titre = (
                        course.nom
                        + " - Classement FFC "
                        + categorie
                    )

                else:

                    titre = (
                        course.nom
                        + " - Classement "
                        + categorie
                    )


                # =================================================
                # FORMAT PDF
                # =================================================

                if format_export == "pdf":

                    contenu = exporter_pdf(
                        resultat,
                        titre
                    )

                    extension = "pdf"


                # =================================================
                # FORMAT PNG
                # =================================================

                elif format_export == "png":

                    contenu = exporter_png(
                        resultat,
                        titre,
                        type_export
                    )

                    extension = "png"


                # =================================================
                # FORMAT EXCEL
                # =================================================

                elif format_export == "excel":

                    contenu = exporter_excel(
                        resultat,
                        titre,
                        type_export
                    )

                    extension = "xlsx"


                # =================================================
                # FORMAT CSV
                # =================================================

                elif format_export == "csv":

                    contenu = exporter_csv(
                        resultat,
                        type_export
                    )

                    extension = "csv"


                # =================================================
                # NOM DU FICHIER
                # =================================================

                nom_fichier = (

                    categorie

                    .replace(
                        "/",
                        "-"
                    )

                    .replace(
                        "\\",
                        "-"
                    )

                    .replace(
                        ":",
                        "-"
                    )

                    .replace(
                        "*",
                        "-"
                    )

                    .replace(
                        "?",
                        "-"
                    )

                    .replace(
                        '"',
                        "-"
                    )

                    .replace(
                        "<",
                        "-"
                    )

                    .replace(
                        ">",
                        "-"
                    )

                    .replace(
                        "|",
                        "-"
                    )

                    + "."
                    + extension
                )


                archive.writestr(
                    nom_fichier,
                    contenu
                )


    # ========================================================
    # RECUPERATION DU ZIP
    # ========================================================

    zip_buffer.seek(0)

    zip_contenu = (
        zip_buffer.getvalue()
    )


    # ========================================================
    # VERIFICATION
    # ========================================================

    if not zip_contenu:

        return (
            "Aucun résultat disponible "
            "pour les catégories sélectionnées.",
            404
        )


    # ========================================================
    # NOM DU ZIP
    # ========================================================

    if mode_ffc:

        nom_zip = (
            "resultats_categories_ffc.zip"
        )

    else:

        nom_zip = (
            "resultats_categories.zip"
        )


    # ========================================================
    # ENVOI
    # ========================================================

    return send_file(

        BytesIO(zip_contenu),

        mimetype="application/zip",

        as_attachment=True,

        download_name=nom_zip
    )

  



# ============================================================
# INITIALISATION DE LA BASE
# ============================================================

Base.metadata.create_all(
    bind=engine
)


with Session() as session:

    course = session.get(
        Course,
        COURSE_ID
    )

    if course is None:

        course = Course(
            id=COURSE_ID,
            nom=COURSE.nom,
            date=COURSE.date,
            lieu=COURSE.lieu
        )

        session.add(course)
        session.commit()


# ============================================================
# LANCEMENT
# ============================================================

def lancer_serveur(
    host,
    port
):

    serveur = make_server(
        host,
        port,
        app,
        threaded=True
    )

    print(
        f"ChronoLive démarré sur "
        f"http://{host}:{port}"
    )

    serveur.serve_forever()


if __name__ == "__main__":

    thread_prive = threading.Thread(
        target=lancer_serveur,
        args=(
            "127.0.0.1",
            PORT_PRIVE
        ),
        daemon=True
    )

    thread_public = threading.Thread(
        target=lancer_serveur,
        args=(
            "0.0.0.0",
            PORT_PUBLIC
        ),
        daemon=True
    )

    thread_prive.start()
    thread_public.start()

    print()
    print(
        "================================"
    )
    print(
        "        CHRONOLIVE"
    )
    print(
        "================================"
    )

    print(
        f"Inscription   : "
        f"http://127.0.0.1:{PORT_PRIVE}/"
    )

    print(
        f"Chronométrage : "
        f"http://127.0.0.1:{PORT_PRIVE}/chronometrage"
    )

    print(
        f"Classement    : "
        f"http://127.0.0.1:{PORT_PUBLIC}/classement_live"
    )

    print(
        f"Résultats     : "
        f"http://127.0.0.1:{PORT_PRIVE}/resultats"
    )

    print()

    print(
        f"Accès Internet : "
        f"{URL_CLASSEMENT_PUBLIC}"
    )

    print()

    print(
        "Pour publier le classement sur Internet, "
        "utiliser dans une invite de commande :"
    )

    print(
        "tailscale funnel 5000"
    )

    print(
        "================================"
    )

    print()

    try:

        while True:
            time.sleep(3600)

    except KeyboardInterrupt:

        print(
            "\nArrêt de ChronoLive."
        )