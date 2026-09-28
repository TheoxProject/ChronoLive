from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Coureur, Arrivee


# ============================================================
# CONFIGURATION
# ============================================================

DATABASE_URL = "sqlite:///chronolive.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine)


# ============================================================
# AJOUT MANUEL D'UNE ARRIVÉE
# ============================================================

def ajouter_arrivee_manuelle(dossard, heure_arrivee, course_id=1):

    db = SessionLocal()

    try:
        # ----------------------------------------------------
        # Recherche du coureur
        # ----------------------------------------------------

        coureur = (
            db.query(Coureur)
            .filter(
                Coureur.dossard == dossard,
                Coureur.course_id == course_id
            )
            .first()
        )

        if coureur is None:
            print(f"Aucun coureur trouvé avec le dossard {dossard}.")
            return

        if coureur.heure_depart is None:
            print("Le coureur n'a pas d'heure de départ.")
            return

        # ----------------------------------------------------
        # Conversion de l'heure d'arrivée
        # ----------------------------------------------------

        timestamp = datetime.strptime(
            heure_arrivee,
            "%H:%M:%S.%f"
        )

        # ----------------------------------------------------
        # Calcul du temps de course
        # ----------------------------------------------------

        depart = datetime.combine(
            timestamp.date(),
            coureur.heure_depart
        )

        temps_centisecondes = round(
            (timestamp - depart).total_seconds() * 100
        )

        if temps_centisecondes < 0:
            print("L'arrivée est avant le départ.")
            return

        # ----------------------------------------------------
        # Création de l'arrivée
        # ----------------------------------------------------

        arrivee = Arrivee(
            timestamp=timestamp,
            dossard_coureur=dossard,
            course_id=course_id
        )

        db.add(arrivee)

        # ----------------------------------------------------
        # Mise à jour du coureur
        # ----------------------------------------------------

        coureur.heure_arrivee = timestamp
        coureur.temps_centisecondes = temps_centisecondes
        coureur.statut = "arrive"

        db.commit()

        print("Arrivée ajoutée avec succès.")
        print(f"Dossard : {dossard}")
        print(f"Départ  : {coureur.heure_depart}")
        print(f"Arrivée : {heure_arrivee}")
        print(f"Temps   : {temps_centisecondes} centisecondes")

    except ValueError:
        print("Format invalide. Utilisez HH:MM:SS.cc")

    except Exception as e:
        db.rollback()
        print(f"Erreur : {e}")

    finally:
        db.close()


# ============================================================
# UTILISATION
# ============================================================

if __name__ == "__main__":

    dossard = int(input("Dossard du coureur : "))

    heure = input(
        "Heure réelle d'arrivée (HH:MM:SS.cc) : "
    )

    ajouter_arrivee_manuelle(
        dossard=dossard,
        heure_arrivee=heure,
        course_id=1
    )