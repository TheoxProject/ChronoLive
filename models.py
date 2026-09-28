from datetime import datetime

from sqlalchemy import (
    Column,
    Date,
    ForeignKey,
    Integer,
    String,
    Time,
    DateTime
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# Classe de base de tous nos modèles SQLAlchemy
class Base(DeclarativeBase):
    pass


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True)
    nom = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    lieu = Column(String, nullable=True)

    coureurs = relationship(
        "Coureur",
        back_populates="course"
    )


class Coureur(Base):
    __tablename__ = "coureurs"

    id = Column(Integer, primary_key=True)

    # ========================================================
    # INFORMATIONS PERSONNELLES
    # ========================================================

    nom = Column(String, nullable=False)
    prenom = Column(String, nullable=False)
    sexe = Column(String, nullable=False)
    date_naissance = Column(Date, nullable=False)

    # ========================================================
    # INFORMATIONS SPORTIVES
    # ========================================================

    licence = Column(String, nullable=True)
    club = Column(String, nullable=True)
    categorie = Column(String, nullable=False)
    categorie_ffc = Column(String, nullable=True)
    
    # ========================================================
    # INFORMATIONS COURSE
    # ========================================================

    dossard = Column(Integer, unique=True, nullable=True)
    heure_depart = Column(Time, nullable=True)

    # Résultats
    heure_arrivee = Column(DateTime, nullable=True)
    temps_centisecondes = Column(Integer, nullable=True)

    # Statut du coureur
    statut = Column(
        String,
        nullable=False,
        default="inscrit"
    )

    # Les coureurs participe à une course
    course_id = Column(
        Integer,
        ForeignKey("courses.id"),
        nullable=False
    )

    course = relationship(
        "Course",
        back_populates="coureurs"
    )


class Arrivee(Base):
    __tablename__ = "arrivees"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    # Heure exacte enregistrée par le chronomètre
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    # Dossard associé après identification
    dossard_coureur: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True
    )

    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id"),
        nullable=False,
        index=True
    )