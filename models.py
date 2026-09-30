# ------------------------------------------------------------
# MODÈLES DE DONNÉES
# ------------------------------------------------------------
# Définition des tables SQLAlchemy utilisées
# par ChronoLive.
#
# Une base SQLite correspond à UNE seule course.
# Les tables Coureur et Arrivee ne possèdent donc
# plus de course_id.
# ------------------------------------------------------------

from datetime import datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Integer,
    String,
    Time,
)

from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)

from config import STATUT_INSCRIT


class Base(DeclarativeBase):
    pass


class Course(Base):
    __tablename__ = "courses"

    # Clé primaire technique obligatoire pour SQLAlchemy.
    # Elle n'est pas utilisée par la logique métier.
    cle = Column(
        Integer,
        primary_key=True,
        default=1
    )

    nom = Column(
        String,
        nullable=False
    )

    date = Column(
        Date,
        nullable=False
    )

    lieu = Column(
        String,
        nullable=True
    )

    type_course = Column(
        String,
        nullable=False
    )

    heure_depart = Column(
        Time,
        nullable=True
    )


class Coureur(Base):
    __tablename__ = "coureurs"

    id = Column(
        Integer,
        primary_key=True
    )

    nom = Column(
        String,
        nullable=False
    )

    prenom = Column(
        String,
        nullable=False
    )

    sexe = Column(
        String,
        nullable=False
    )

    date_naissance = Column(
        Date,
        nullable=False
    )

    licence = Column(
        String,
        nullable=True
    )

    club = Column(
        String,
        nullable=True
    )

    categorie = Column(
        String,
        nullable=False
    )

    categorie_ffc = Column(
        String,
        nullable=True
    )

    dossard = Column(
        Integer,
        unique=True,
        nullable=True
    )

    heure_depart = Column(
        Time,
        nullable=True
    )

    heure_arrivee = Column(
        Time,
        nullable=True
    )

    temps_centisecondes = Column(
        Integer,
        nullable=True
    )

    statut = Column(
        String,
        nullable=False,
        default=STATUT_INSCRIT
    )


class Arrivee(Base):
    __tablename__ = "arrivees"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    dossard_coureur: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True
    )

