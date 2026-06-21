import cv2
import mediapipe as mp
import math
import json
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# ============================================================
# Pozitii de referinta pentru fiecare miscare
# Bazate pe descrierile reale ale pasilor de dans
# ============================================================

REFERINTE = {
    "chacha_basic": {
        "nume": "Basic Movement",
        "dans": "Cha-Cha-Cha",
        "descriere": "Stangul inainte, greutate pe dreptul, cha-cha-cha lateral",
        "conditii": {
            "genunchi_indoiti": True,
            "greutate": "dreapta",
            "directie": "inainte"
        }
    },
    "jive_basic": {
        "nume": "Basic In Place",
        "dans": "Jive",
        "descriere": "Stangul inapoi (rock step), revenire pe dreptul",
        "conditii": {
            "genunchi_indoiti": True,
            "greutate": "stanga",
            "directie": "inapoi"
        }
    },
    "vals_closed": {
        "nume": "Closed Change",
        "dans": "Vals Lent",
        "descriere": "Stang inainte, drept langa, stang langa",
        "conditii": {
            "genunchi_indoiti": False,
            "greutate": "stanga",
            "directie": "inainte"
        }
    },
    "quickstep_quarter": {
        "nume": "Quarter Turn to Right",
        "dans": "Quickstep",
        "descriere": "Stang inainte, rotatie spre dreapta",
        "conditii": {
            "genunchi_indoiti": True,
            "greutate": "stanga",
            "directie": "inainte"
        }
    }
}

def calculeaza_unghi(a, b, c):
    """Calculeaza unghiul dintre 3 puncte in grade"""
    try:
        ax, ay = a.x, a.y
        bx, by = b.x, b.y
        cx, cy = c.x, c.y

        ab = math.sqrt((bx-ax)**2 + (by-ay)**2)
        bc = math.sqrt((cx-bx)**2 + (cy-by)**2)
        ac = math.sqrt((cx-ax)**2 + (cy-ay)**2)

        if ab * bc == 0:
            return 180

        cos_unghi = (ab**2 + bc**2 - ac**2) / (2 * ab * bc)
        cos_unghi = max(-1, min(1, cos_unghi))
        unghi = math.degrees(math.acos(cos_unghi))
        return unghi
    except:
        return 180

def analizeaza_picioare(landmarks):
    """
    Analizeaza pozitia picioarelor si returneaza feedback
    Puncte MediaPipe folosite:
    23 = sold stang, 24 = sold drept
    25 = genunchi stang, 26 = genunchi drept
    27 = glezna stanga, 28 = glezna dreapta
    31 = deget picior stang, 32 = deget picior drept
    """
    try:
        sold_stang    = landmarks[23]
        sold_drept    = landmarks[24]
        genunchi_stang = landmarks[25]
        genunchi_drept = landmarks[26]
        glezna_stanga  = landmarks[27]
        glezna_dreapta = landmarks[28]
        deget_stang    = landmarks[31]
        deget_drept    = landmarks[32]

        # Unghi genunchi (sold-genunchi-glezna)
        unghi_gen_stang = calculeaza_unghi(
            sold_stang, genunchi_stang, glezna_stanga
        )
        unghi_gen_drept = calculeaza_unghi(
            sold_drept, genunchi_drept, glezna_dreapta
        )

        # Genunchii indoiti = unghi < 160 grade
        gen_stang_indoit = unghi_gen_stang < 160
        gen_drept_indoit = unghi_gen_drept < 160

        # Care picior e mai in fata (coordonata Y mai mica = mai sus pe ecran)
        # In MediaPipe: Y creste in jos, deci Y mai mare = mai in fata
        picior_stang_y = glezna_stanga.y
        picior_drept_y = glezna_dreapta.y
        diferenta_y    = abs(picior_stang_y - picior_drept_y)

        picior_in_fata = None
        if diferenta_y > 0.03:  # Diferenta semnificativa
            if picior_stang_y > picior_drept_y:
                picior_in_fata = "stang"
            else:
                picior_in_fata = "drept"

        # Distanta dintre picioare (laterala)
        distanta_laterala = abs(glezna_stanga.x - glezna_dreapta.x)

        # Greutatea corpului (sold mai coborat = greutate acolo)
        if sold_stang.y > sold_drept.y + 0.02:
            greutate = "stanga"
        elif sold_drept.y > sold_stang.y + 0.02:
            greutate = "dreapta"
        else:
            greutate = "centru"

        return {
            "unghi_gen_stang":    round(unghi_gen_stang),
            "unghi_gen_drept":    round(unghi_gen_drept),
            "gen_stang_indoit":   gen_stang_indoit,
            "gen_drept_indoit":   gen_drept_indoit,
            "picior_in_fata":     picior_in_fata,
            "greutate":           greutate,
            "distanta_laterala":  round(distanta_laterala, 3),
            "diferenta_y":        round(diferenta_y, 3)
        }
    except Exception as e:
        return None

def genereaza_feedback(analiza, dans_context=None):
    """
    Genereaza mesaje de feedback prietenoase
    bazate pe analiza picioarelor
    """
    if not analiza:
        return {
            "mesaj":  "Pozitioneaza-te mai aproape de camera",
            "tip":    "info",
            "scor":   0
        }

    mesaje = []
    scor   = 100

    # Verifica genunchii
    gen_st = analiza["gen_stang_indoit"]
    gen_dr = analiza["gen_drept_indoit"]
    ung_st = analiza["unghi_gen_stang"]
    ung_dr = analiza["unghi_gen_drept"]

    if not gen_st and not gen_dr:
        mesaje.append("Incearca sa indoi putin genunchii --- dansul are nevoie de flexibilitate!")
        scor -= 25
    elif not gen_st:
        mesaje.append("Genunchiul stang pare cam rigid --- relaxeaza-l putin")
        scor -= 15
    elif not gen_dr:
        mesaje.append("Genunchiul drept poate fi putin mai flexibil")
        scor -= 15

    # Verifica daca un picior e in fata
    picior = analiza["picior_in_fata"]
    greutate = analiza["greutate"]

    if dans_context == "chacha":
        if picior == "stang":
            mesaje.append("Stangul e in fata --- pozitie buna pentru Cha-Cha-Cha!")
            scor += 10
        elif picior == "drept":
            mesaje.append("Incearca sa pornesti cu stangul inainte la Cha-Cha-Cha")
            scor -= 10

    elif dans_context == "jive":
        if picior == "stang" and greutate == "dreapta":
            mesaje.append("Rock step corect --- stangul inapoi, greutatea pe dreptul!")
            scor += 10
        elif picior is None:
            mesaje.append("La Jive, stangul pleaca putin inapoi --- incearca rock step-ul!")
            scor -= 10

    elif dans_context == "vals":
        if gen_st and gen_dr and ung_st > 140 and ung_dr > 140:
            mesaje.append("Picioarele sunt elegante --- perfect pentru Vals!")
            scor += 10
        else:
            mesaje.append("In Vals, picioarele sunt mai intinse si elegante")
            scor -= 10

    elif dans_context == "quickstep":
        if gen_st and gen_dr:
            mesaje.append("Genunchii activi --- exact ce trebuie pentru Quickstep!")
            scor += 10

    # Distanta dintre picioare
    dist = analiza["distanta_laterala"]
    if dist < 0.05:
        mesaje.append("Picioarele sunt cam lipite --- un pic mai mult spatiu intre ele")
        scor -= 10
    elif dist > 0.35:
        mesaje.append("Picioarele sunt cam departate --- apropie-le putin")
        scor -= 10

    # Scor final si mesaj principal
    scor = max(0, min(100, scor))

    if scor >= 80:
        mesaj_principal = "Foarte bine! Pozitia picioarelor e corecta!"
        tip = "succes"
    elif scor >= 60:
        mesaj_principal = "Aproape perfect! Mici ajustari si va fi excelent!"
        tip = "bine"
    elif scor >= 40:
        mesaj_principal = "Continua sa exersezi --- esti pe drumul cel bun!"
        tip = "atentie"
    else:
        mesaj_principal = "Nu te descuraja! Fiecare dansator a inceput de undeva!"
        tip = "incurajare"

    return {
        "mesaj":        mesaj_principal,
        "detalii":      mesaje[:2],  # Maxim 2 detalii
        "tip":          tip,
        "scor":         scor,
        "analiza":      analiza
    }

def genereaza_frames(dans_context=None):
    """Generator principal pentru fluxul video"""
    camera = cv2.VideoCapture(0)

    base_options = python.BaseOptions(
        model_asset_path='pose_landmarker.task'
    )
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        output_segmentation_masks=False
    )
    detector = vision.PoseLandmarker.create_from_options(options)

    frame_count = 0

    while True:
        success, frame = camera.read()
        if not success:
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image  = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=frame_rgb
        )
        rezultat = detector.detect(mp_image)

        feedback_data = None

        if rezultat.pose_landmarks:
            landmarks = rezultat.pose_landmarks[0]

            # Deseneaza punctele articulatiilor
            for i, landmark in enumerate(landmarks):
                h, w, _ = frame.shape
                cx = int(landmark.x * w)
                cy = int(landmark.y * h)

                # Picioare (23-32) in auriu mai mare
                if 23 <= i <= 32:
                    cv2.circle(frame, (cx, cy), 7,
                               (198, 168, 76), -1)
                    cv2.circle(frame, (cx, cy), 9,
                               (230, 200, 100), 2)
                else:
                    cv2.circle(frame, (cx, cy), 4,
                               (150, 130, 60), -1)

            # Deseneaza linii pentru picioare
            conexiuni_picioare = [
                (23, 25), (25, 27), (27, 31),  # Picior stang
                (24, 26), (26, 28), (28, 32),  # Picior drept
                (23, 24)  # Linia soldurilor
            ]

            for start_idx, end_idx in conexiuni_picioare:
                try:
                    s = landmarks[start_idx]
                    e = landmarks[end_idx]
                    h, w, _ = frame.shape
                    pt1 = (int(s.x * w), int(s.y * h))
                    pt2 = (int(e.x * w), int(e.y * h))
                    cv2.line(frame, pt1, pt2,
                             (198, 168, 76), 2)
                except:
                    pass

            # Analizeaza picioarele la fiecare 10 frame-uri
            if frame_count % 10 == 0:
                analiza   = analizeaza_picioare(landmarks)
                feedback_data = genereaza_feedback(
                    analiza, dans_context
                )

        frame_count += 1

        # Codificam frame-ul
        ret, buffer   = cv2.imencode('.jpg', frame)
        frame_bytes   = buffer.tobytes()

        # Adaugam feedback ca header custom
        if feedback_data:
            feedback_json = json.dumps(
                feedback_data, ensure_ascii=False
            )
        else:
            feedback_json = json.dumps({
                "mesaj": "Detectez miscarea...",
                "tip": "info",
                "scor": 0
            })

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n'
               b'X-Feedback: ' +
               feedback_json.encode('utf-8') +
               b'\r\n\r\n' +
               frame_bytes + b'\r\n')

    camera.release()