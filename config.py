# ============================================================
# CONFIGURATION CHRONOLIVE
# ============================================================
from dataclasses import dataclass
from datetime import date

# Séparation des routes pour plus de sécurité, les spectateur ne doivent pas avoir accès au logiciel de gestion de la course
PORT_PUBLIC = 5000  # classement public, accessible par internet via Tailscale Funnel
PORT_PRIVE = 5001   # administration et chronométrage, accessible uniquement depuis le PC de course

# Nom de la database
DATABASE_URL = "sqlite:///chronolive.db"

@dataclass
class CourseConfig:

    nom: str
    date: date
    lieu: str


COURSE = CourseConfig(
    nom = "CLM de l'OMS",
    date = date(2026, 9, 20),
    lieu = "Thonon Les Bains"
)



# Catégories récompensées, disponibles pour les inscriptions
CATEGORIES = [
    "U15",
    "U17",
    "U19",
    "Access",
    "Open",
    "Femme",
    "NL",
]

# Catégories FFC disponibles pour les inscriptions
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


# URL publique du classement via Tailscale Funnel
URL_CLASSEMENT_PUBLIC = (
    "https://theoxzenbook.tail7f7f8c.ts.net/"
    "classement_live"
)