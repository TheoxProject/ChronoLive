#-----------
# DATABASE
#-----------
# Gestion de la connexion à la base SQLite
# et des sessions SQLAlchemy.
#
# Création des tables au démarrage de ChronoLive.
#-----------

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import DATABASE_URL
from models import Base


# Connexion à la base de données
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)


# Créateur de sessions SQLAlchemy
Session = sessionmaker(bind=engine)


def initialiser_base():
    # Crée les tables définies dans models.py
    # si elles n'existent pas encore.
    Base.metadata.create_all(bind=engine)