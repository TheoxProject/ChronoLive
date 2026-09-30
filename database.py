# ------------------------------------------------------------
# DATABASE
# ------------------------------------------------------------
# Gestion des bases SQLite et des sessions SQLAlchemy.
#
# Une base SQLite correspond à une seule course.
# La base utilisée par ChronoLive est configurée une seule fois
# au démarrage du logiciel, après sélection de la course.
# ------------------------------------------------------------

import re
import unicodedata

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import COURSES_DIR
from models import Base, Course


# ------------------------------------------------------------
# SESSION SQLALCHEMY
# ------------------------------------------------------------

# Le sessionmaker existe dès l'import du module.
# Il est lié à la base choisie au lancement de ChronoLive.
Session = sessionmaker()

# Engine de la base actuellement utilisée.
engine = None

# Indicateur interne :
# False = aucune base n'a encore été initialisée.
# True  = une base a été sélectionnée et configurée.
base_initialisee = False


# ------------------------------------------------------------
# UTILITAIRES
# ------------------------------------------------------------

def nettoyer_nom_fichier(nom):
    """
    Transforme le nom de la course en nom de fichier lisible
    et compatible avec Windows.
    """

    nom = unicodedata.normalize(
        "NFKD",
        nom
    ).encode(
        "ascii",
        "ignore"
    ).decode(
        "ascii"
    )

    nom = re.sub(
        r"[^a-zA-Z0-9]+",
        "_",
        nom
    )

    nom = nom.strip("_")

    return nom or "Course"


def chemin_course(
    nom,
    date_course
):
    """
    Génère le nom de fichier SQLite d'une course.

    Exemple :
    2026-08-29_Grimpee_de_Trechaufte.db
    """

    nom_fichier = (
        f"{date_course.isoformat()}_"
        f"{nettoyer_nom_fichier(nom)}.db"
    )

    return COURSES_DIR / nom_fichier


def construire_url_sqlite(
    chemin
):
    """
    Construit l'URL SQLAlchemy correspondant à une base SQLite.
    """

    chemin = Path(chemin).resolve()

    return f"sqlite:///{chemin.as_posix()}"


# ------------------------------------------------------------
# ÉTAT DE LA BASE
# ------------------------------------------------------------

def base_est_initialisee():
    """
    Retourne True si une base de course est actuellement
    configurée pour ChronoLive.
    """

    return base_initialisee


# ------------------------------------------------------------
# CRÉATION D'UNE BASE
# ------------------------------------------------------------

def creer_base_course(
    nom,
    date_course,
    lieu,
    type_course,
    heure_depart
):
    """
    Crée une nouvelle base SQLite pour une course.

    Retourne le chemin de la base créée.
    """

    COURSES_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    chemin = chemin_course(
        nom,
        date_course
    )

    # Si le nom de fichier existe déjà, on ajoute un suffixe.
    # Exemple :
    # 2026-09-20_CLM_OMS.db
    # 2026-09-20_CLM_OMS_2.db
    # 2026-09-20_CLM_OMS_3.db
    compteur = 2

    chemin_original = chemin

    while chemin.exists():

        chemin = (
            chemin_original.parent
            / (
                f"{chemin_original.stem}_"
                f"{compteur}"
                f"{chemin_original.suffix}"
            )
        )

        compteur += 1

    nouvel_engine = create_engine(
        construire_url_sqlite(chemin),
        connect_args={
            "check_same_thread": False
        }
    )

    try:

        # Création des tables.
        Base.metadata.create_all(
            bind=nouvel_engine
        )

        SessionCourse = sessionmaker(
            bind=nouvel_engine
        )

        session = SessionCourse()

        try:

            course = Course(
                nom=nom,
                date=date_course,
                lieu=lieu,
                type_course=type_course,
                heure_depart=heure_depart,
            )

            session.add(course)
            session.commit()

        except Exception:

            session.rollback()
            raise

        finally:

            session.close()

    finally:

        nouvel_engine.dispose()

    return chemin


# ------------------------------------------------------------
# INITIALISATION DE LA BASE
# ------------------------------------------------------------

def initialiser_base(
    chemin
):
    """
    Configure ChronoLive pour utiliser la DB sélectionnée.

    Cette fonction est appelée une seule fois au lancement,
    après sélection ou création d'une course.
    """

    global engine
    global base_initialisee

    chemin = Path(chemin).resolve()

    if not chemin.exists():
        raise FileNotFoundError(
            f"Base de données introuvable : {chemin}"
        )

    if not chemin.is_file():
        raise ValueError(
            f"Le chemin indiqué n'est pas un fichier : {chemin}"
        )

    engine = create_engine(
        construire_url_sqlite(chemin),
        connect_args={
            "check_same_thread": False
        }
    )

    # On s'assure que les tables existent.
    Base.metadata.create_all(
        bind=engine
    )

    # Toutes les nouvelles sessions utiliseront cette base.
    Session.configure(
        bind=engine
    )

    base_initialisee = True


# ------------------------------------------------------------
# INFORMATIONS D'UNE COURSE
# ------------------------------------------------------------

def lire_course(
    chemin
):
    """
    Lit les informations de la course contenue dans une DB
    sans modifier la DB utilisée par ChronoLive.
    """

    chemin = Path(chemin).resolve()

    if not chemin.exists():
        raise FileNotFoundError(
            f"Base de données introuvable : {chemin}"
        )

    temp_engine = create_engine(
        construire_url_sqlite(chemin),
        connect_args={
            "check_same_thread": False
        }
    )

    TempSession = sessionmaker(
        bind=temp_engine
    )

    session = TempSession()

    try:

        course = session.query(
            Course
        ).first()

        if course is None:
            return None

        return {
            "nom": course.nom,
            "date": course.date,
            "lieu": course.lieu,
            "type_course": course.type_course,
            "heure_depart": course.heure_depart,
        }

    finally:

        session.close()
        temp_engine.dispose()


# ------------------------------------------------------------
# LISTE DES COURSES
# ------------------------------------------------------------

def lister_courses():
    """
    Retourne toutes les bases de courses disponibles.

    Chaque élément contient :
    - le chemin du fichier ;
    - les informations de la course.
    """

    COURSES_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    courses = []

    for chemin in sorted(
        COURSES_DIR.glob("*.db")
    ):

        try:

            course = lire_course(
                chemin
            )

            # Ignore les fichiers SQLite ne contenant pas
            # une course ChronoLive valide.
            if course is None:
                continue

            courses.append({
                "fichier": chemin,
                **course,
            })

        except Exception:
            # Une base invalide ne doit pas empêcher
            # l'affichage des autres courses.
            continue

    return courses

