# ============================================================
# CONFIGURATION CHRONOLIVE
# ============================================================

from pathlib import Path


# ------------------------------------------------------------
# SERVEURS
# ------------------------------------------------------------

PORT_PUBLIC = 5000
PORT_PRIVE = 5001


# ------------------------------------------------------------
# BASES DE DONNÉES
# ------------------------------------------------------------

# Répertoire de base de ChronoLive.
BASE_DIR = Path(__file__).resolve().parent

# Toutes les bases SQLite des courses sont stockées ici.
COURSES_DIR = BASE_DIR / "courses"


# ------------------------------------------------------------
# TYPES DE COURSE
# ------------------------------------------------------------

TYPE_CLM = "CLM"
TYPE_GRIMPEE = "Grimpée"
TYPE_CRITERIUM = "Critérium"

TYPES_COURSE = (
    TYPE_CLM,
    TYPE_GRIMPEE,
    TYPE_CRITERIUM,
)


# ------------------------------------------------------------
# STATUTS DES COUREURS
# ------------------------------------------------------------

STATUT_INSCRIT = "inscrit"
STATUT_PRET = "pret"
STATUT_ARRIVE = "arrive"
STATUT_DNS = "dns"
STATUT_DNF = "dnf"
STATUT_DSQ = "dsq"

STATUTS = (
    STATUT_INSCRIT,
    STATUT_PRET,
    STATUT_ARRIVE,
    STATUT_DNS,
    STATUT_DNF,
    STATUT_DSQ,
)


# ------------------------------------------------------------
# STATUTS PRIS EN COMPTE DANS LE CLASSEMENT
# ------------------------------------------------------------

STATUTS_CLASSEMENT = (
    STATUT_ARRIVE,
    STATUT_DNF,
    STATUT_DNS,
    STATUT_DSQ,
)


# ------------------------------------------------------------
# CATÉGORIES
# ------------------------------------------------------------

CATEGORIES = [
    "U15",
    "U17",
    "U19",
    "Access",
    "Open",
    "Femme",
    "NL",
]


CATEGORIES_FFC = [
    "U15",
    "U17",
    "U19",
    "Access1",
    "Access2",
    "Access3",
    "Access4",
    "Open1",
    "Open2",
    "Open3",
    "Elite",
]


# ------------------------------------------------------------
# URL PUBLIQUE
# ------------------------------------------------------------

URL_CLASSEMENT_PUBLIC = (
    "https://theoxzenbook.tail7f7f8c.ts.net/"
    "classement_live"
)