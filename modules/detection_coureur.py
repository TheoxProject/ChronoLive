# ------------------------------------------------------------
# MODULE - DETECTION COUREUR
# ------------------------------------------------------------
# Acquisition vidéo + détection des coureurs.
#
# Étape actuelle :
# - réception des images du téléphone
# - détection des personnes et vélos avec YOLO
# - tracking
# - association personne / vélo
# - visualisation des détections
#
# Étapes futures :
# - détection du dossard
# - lecture du numéro
# - accumulation de confiance
# - détection de la ligne d'arrivée
# - génération du timestamp de passage
# - envoi de l'arrivée à ChronoLive
#
# Routes :
# - /detection_coureur/camera
# - /detection_coureur/frame
# - /detection_coureur/monitor
# - /detection_coureur/flux
# - /detection_coureur/status
# ------------------------------------------------------------

import threading
import time

import cv2
import numpy as np

from flask import (
    Blueprint,
    Response,
    jsonify,
    render_template,
    request,
)

from ultralytics import YOLO

from config import (
    YOLO_MODELE_DETECTION,
    YOLO_DETECTION_IMGSZ,
    YOLO_DETECTION_CONF,
)


detection_coureur_bp = Blueprint(
    "detection_coureur",
    __name__
)


# ------------------------------------------------------------
# MODELE YOLO
# ------------------------------------------------------------

modele = YOLO(
    YOLO_MODELE_DETECTION
)


# Classes COCO utilisées :
#
# 0 = person
# 1 = bicycle

CLASSE_PERSONNE = 0
CLASSE_VELO = 1


# ------------------------------------------------------------
# ETAT DU FLUX
# ------------------------------------------------------------

derniere_image = None

numero_image = 0

derniere_reception = None

nombre_cyclistes = 0

temps_inference_ms = 0.0


condition_image = threading.Condition()

lock_inference = threading.Lock()


# ------------------------------------------------------------
# OUTILS GEOMETRIQUES
# ------------------------------------------------------------

def calculer_iou(
    boite_a,
    boite_b
):
    """
    Calcule l'IoU entre deux bounding boxes.

    Format :
        [x1, y1, x2, y2]
    """

    ax1, ay1, ax2, ay2 = boite_a

    bx1, by1, bx2, by2 = boite_b


    intersection_x1 = max(
        ax1,
        bx1
    )

    intersection_y1 = max(
        ay1,
        by1
    )

    intersection_x2 = min(
        ax2,
        bx2
    )

    intersection_y2 = min(
        ay2,
        by2
    )


    largeur = max(
        0,
        intersection_x2
        - intersection_x1
    )

    hauteur = max(
        0,
        intersection_y2
        - intersection_y1
    )


    aire_intersection = (
        largeur * hauteur
    )


    aire_a = (
        max(
            0,
            ax2 - ax1
        )
        *
        max(
            0,
            ay2 - ay1
        )
    )


    aire_b = (
        max(
            0,
            bx2 - bx1
        )
        *
        max(
            0,
            by2 - by1
        )
    )


    union = (
        aire_a
        + aire_b
        - aire_intersection
    )


    if union <= 0:

        return 0.0


    return (
        aire_intersection
        / union
    )



def associer_personnes_velos(
    personnes,
    velos
):
    """
    Associe approximativement chaque personne
    à un vélo.

    Cette logique est volontairement simple pour
    le premier prototype.

    L'association sera améliorée plus tard pour
    les pelotons et les occlusions.
    """

    associations = []

    velos_utilises = set()


    for personne_index, personne in enumerate(
        personnes
    ):

        boite_personne = personne["bbox"]

        px1, py1, px2, py2 = (
            boite_personne
        )


        largeur_personne = (
            px2 - px1
        )

        hauteur_personne = (
            py2 - py1
        )


        if (
            largeur_personne <= 0
            or hauteur_personne <= 0
        ):

            continue


        # Extension de la boîte vers le bas.
        #
        # Un cycliste est généralement au-dessus
        # de son vélo.

        boite_etendue = [
            px1
            - largeur_personne * 0.5,

            py1,

            px2
            + largeur_personne * 0.5,

            py2
            + hauteur_personne * 0.8,
        ]


        meilleur_velo = None

        meilleure_score = 0.0


        for velo_index, velo in enumerate(
            velos
        ):

            if velo_index in velos_utilises:

                continue


            boite_velo = velo["bbox"]


            iou = calculer_iou(
                boite_etendue,
                boite_velo
            )


            vx1, vy1, vx2, vy2 = (
                boite_velo
            )


            centre_velo_x = (
                vx1 + vx2
            ) / 2


            centre_personne_x = (
                px1 + px2
            ) / 2


            distance_x = abs(
                centre_velo_x
                - centre_personne_x
            )


            # Distance horizontale normalisée.
            distance_x_normalisee = (
                distance_x
                / largeur_personne
            )


            if (
                distance_x_normalisee
                > 1.2
            ):

                continue


            score = iou


            if score > meilleure_score:

                meilleure_score = score

                meilleur_velo = (
                    velo_index
                )


        if (
            meilleur_velo is not None
            and meilleure_score >= 0.03
        ):

            associations.append({

                "personne_index":
                    personne_index,

                "velo_index":
                    meilleur_velo,

                "score":
                    meilleure_score,

            })


            velos_utilises.add(
                meilleur_velo
            )


    return associations


# ------------------------------------------------------------
# TRAITEMENT YOLO
# ------------------------------------------------------------

def traiter_image(
    image
):
    """
    Effectue la détection et le tracking
    sur une image OpenCV.

    Retourne :
    - image annotée
    - nombre de cyclistes détectés
    """

    global temps_inference_ms


    debut = time.perf_counter()


    with lock_inference:

        resultats = modele.track(

            image,

            persist=True,

            classes=[
                CLASSE_PERSONNE,
                CLASSE_VELO,
            ],

            conf=YOLO_DETECTION_CONF,

            imgsz=YOLO_DETECTION_IMGSZ,

            verbose=False,

        )


    temps_inference_ms = (
        time.perf_counter()
        - debut
    ) * 1000


    resultat = resultats[0]


    personnes = []

    velos = []


    if resultat.boxes is not None:

        boites = (
            resultat.boxes.xyxy
            .cpu()
            .numpy()
        )


        classes = (
            resultat.boxes.cls
            .cpu()
            .numpy()
        )


        confiances = (
            resultat.boxes.conf
            .cpu()
            .numpy()
        )


        ids = None


        if resultat.boxes.id is not None:

            ids = (
                resultat.boxes.id
                .cpu()
                .numpy()
            )


        for index, boite in enumerate(
            boites
        ):

            classe = int(
                classes[index]
            )


            confiance = float(
                confiances[index]
            )


            track_id = None


            if ids is not None:

                track_id = int(
                    ids[index]
                )


            detection = {

                "bbox":
                    boite.tolist(),

                "confidence":
                    confiance,

                "track_id":
                    track_id,

            }


            if classe == CLASSE_PERSONNE:

                personnes.append(
                    detection
                )


            elif classe == CLASSE_VELO:

                velos.append(
                    detection
                )


    associations = (
        associer_personnes_velos(
            personnes,
            velos
        )
    )


    nombre_cyclistes = len(
        associations
    )


    # --------------------------------------------------------
    # ANNOTATION
    # --------------------------------------------------------

    image_annotee = (
        resultat.plot(
            labels=True,
            conf=True,
            boxes=True,
        )
    )


    # --------------------------------------------------------
    # AJOUT DES LABELS CYCLISTES
    # --------------------------------------------------------

    for association in associations:

        personne = personnes[association["personne_index"]]


        x1, y1, x2, y2 = (
            map(
                int,
                personne["bbox"]
            )
        )


        track_id = (
            personne["track_id"]
        )


        confiance = (
            personne["confidence"]
        )


        texte = "CYCLISTE"


        if track_id is not None:

            texte += (
                f" · Track {track_id}"
            )


        texte += (
            f" · {confiance:.0%}"
        )


        cv2.rectangle(

            image_annotee,

            (
                x1,
                y1
            ),

            (
                x2,
                y2
            ),

            (
                0,
                255,
                0
            ),

            3,

        )


        cv2.putText(

            image_annotee,

            texte,

            (
                x1,
                max(
                    25,
                    y1 - 10
                )
            ),

            cv2.FONT_HERSHEY_SIMPLEX,

            0.65,

            (
                0,
                255,
                0
            ),

            2,

            cv2.LINE_AA,

        )


    # --------------------------------------------------------
    # INFORMATIONS SYSTEME
    # --------------------------------------------------------

    texte_info = (

        f"Cyclistes : "
        f"{nombre_cyclistes}"
        f"    "

        f"Inference : "
        f"{temps_inference_ms:.0f} ms"
    )


    cv2.rectangle(

        image_annotee,

        (
            10,
            10
        ),

        (
            390,
            50
        ),

        (
            8,
            26,
            47
        ),

        -1,

    )


    cv2.putText(

        image_annotee,

        texte_info,

        (
            20,
            38
        ),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.65,

        (
            255,
            255,
            255
        ),

        2,

        cv2.LINE_AA,

    )


    return (
        image_annotee,
        nombre_cyclistes,
    )


# ------------------------------------------------------------
# PAGE CAMERA - TELEPHONE
# ------------------------------------------------------------

@detection_coureur_bp.route(
    "/detection_coureur/camera"
)
def camera():

    return render_template(
        "detection_camera.html"
    )


# ------------------------------------------------------------
# RECEPTION D'UNE IMAGE
# ------------------------------------------------------------

@detection_coureur_bp.route(
    "/detection_coureur/frame",
    methods=["POST"]
)
def recevoir_frame():

    global derniere_image
    global numero_image
    global derniere_reception
    global nombre_cyclistes


    image_bytes = request.get_data()


    if not image_bytes:

        return (
            "Image vide",
            400
        )


    # --------------------------------------------------------
    # DECODAGE JPEG
    # --------------------------------------------------------

    tableau = np.frombuffer(
        image_bytes,
        dtype=np.uint8
    )


    image = cv2.imdecode(
        tableau,
        cv2.IMREAD_COLOR
    )


    if image is None:

        return (
            "Image JPEG invalide",
            400
        )


    # --------------------------------------------------------
    # DETECTION
    # --------------------------------------------------------

    image_annotee, nombre = (
        traiter_image(
            image
        )
    )


    # --------------------------------------------------------
    # ENCODAGE JPEG
    # --------------------------------------------------------

    succes, buffer = (
        cv2.imencode(
            ".jpg",
            image_annotee,
            [
                cv2.IMWRITE_JPEG_QUALITY,
                80,
            ]
        )
    )


    if not succes:

        return (
            "Impossible d'encoder l'image",
            500
        )


    image_bytes_annotee = (
        buffer.tobytes()
    )


    # --------------------------------------------------------
    # MISE A JOUR DU FLUX
    # --------------------------------------------------------

    with condition_image:

        derniere_image = (
            image_bytes_annotee
        )

        numero_image += 1

        derniere_reception = (
            time.time()
        )

        nombre_cyclistes = (
            nombre
        )

        condition_image.notify_all()


    return (
        "",
        204
    )


# ------------------------------------------------------------
# PAGE MONITORING - PC
# ------------------------------------------------------------

@detection_coureur_bp.route(
    "/detection_coureur/monitor"
)
def monitor():

    return render_template(
        "detection_monitor.html"
    )


# ------------------------------------------------------------
# FLUX VIDEO MJPEG
# ------------------------------------------------------------

@detection_coureur_bp.route(
    "/detection_coureur/flux"
)
def flux():

    def generate():

        dernier_numero = 0


        while True:

            with condition_image:

                while (
                    derniere_image is None
                    or numero_image
                    == dernier_numero
                ):

                    condition_image.wait(
                        timeout=1
                    )


                image = (
                    derniere_image
                )


                dernier_numero = (
                    numero_image
                )


            yield (

                b"--frame\r\n"

                b"Content-Type: "
                b"image/jpeg\r\n"

                b"Content-Length: "
                + str(
                    len(image)
                ).encode()

                + b"\r\n\r\n"

                + image

                + b"\r\n"

            )


    return Response(

        generate(),

        mimetype=(
            "multipart/x-mixed-replace;"
            " boundary=frame"
        ),

        headers={

            "Cache-Control":
                "no-cache",

            "Pragma":
                "no-cache",

        },

    )


# ------------------------------------------------------------
# ETAT DU SYSTEME
# ------------------------------------------------------------

@detection_coureur_bp.route(
    "/detection_coureur/status"
)
def status():

    with condition_image:

        if (
            derniere_reception
            is None
        ):

            return jsonify({

                "connectee":
                    False,

                "numero_image":
                    0,

                "nombre_cyclistes":
                    0,

                "inference_ms":
                    0,

            })


        age = (
            time.time()
            - derniere_reception
        )


        return jsonify({

            "connectee":
                age < 2,

            "numero_image":
                numero_image,

            "nombre_cyclistes":
                nombre_cyclistes,

            "inference_ms":
                round(
                    temps_inference_ms,
                    1
                ),

        })