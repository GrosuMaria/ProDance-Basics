from flask import Flask, render_template, request, redirect, url_for, session, Response
from dance_data import dansuri
from database import initializare, inregistrare, login, get_progres, salveaza_progres, salveaza_sesiune, get_istoric
try:
    from camera import genereaza_frames
    CAMERA_DISPONIBILA = True
except:
    CAMERA_DISPONIBILA = False

app = Flask(__name__)
app.secret_key = "danceapp2024"

@app.route("/")
def index():
    return render_template("login.html")

@app.route("/inregistrare", methods=["GET", "POST"])
def inregistrare_route():
    if request.method == "POST":
        username = request.form["username"]
        parola = request.form["parola"]
        caracter = request.form["character"]
        succes, mesaj = inregistrare(username, parola, caracter)
        if succes:
            return render_template("login.html", succes="Cont creat! Te poti autentifica acum.")
        return render_template("register.html", eroare=mesaj)
    return render_template("register.html")

@app.route("/login", methods=["POST"])
def login_route():
    username = request.form["username"]
    parola = request.form["parola"]
    succes, rezultat = login(username, parola)
    if succes:
        session["username"] = rezultat["username"]
        session["character"] = rezultat["caracter"]
        salveaza_sesiune(username)
        return redirect(url_for("home"))
    return render_template("login.html", eroare=rezultat)

@app.route("/home")
def home():
    if "username" not in session:
        return redirect(url_for("index"))
    return render_template("home.html", username=session["username"])

@app.route("/dans/<nume_dans>")
def dans(nume_dans):
    if "username" not in session:
        return redirect(url_for("index"))
    if nume_dans not in dansuri:
        return redirect(url_for("home"))
    dan = dansuri[nume_dans]
    progres = get_progres(session["username"], nume_dans)
    salveaza_sesiune(session["username"], dan["nume"])
    return render_template("dance.html", dans=dan, dans_nume=nume_dans, username=session["username"], progres=progres)

@app.route("/finalizeaza/<nume_dans>/<int:miscare_id>", methods=["POST"])
def finalizeaza(nume_dans, miscare_id):
    if "username" not in session:
        return redirect(url_for("index"))
    salveaza_progres(session["username"], nume_dans, miscare_id, 1)
    return redirect(url_for("dans", nume_dans=nume_dans))

@app.route("/progres")
def progres():
    if "username" not in session:
        return redirect(url_for("index"))
    rezultate = {}
    for nume_dans, date_dans in dansuri.items():
        progres_dans = get_progres(session["username"], nume_dans)
        total = len(date_dans["miscari"])
        finalizate = sum(1 for v in progres_dans.values() if v == 1)
        rezultate[nume_dans] = {
            "nume": date_dans["nume"],
            "categorie": date_dans["categorie"],
            "total": total,
            "finalizate": finalizate
        }
    return render_template("progress.html",
                         rezultate=rezultate,
                         username=session["username"])

@app.route("/istoric")
def istoric():
    if "username" not in session:
        return redirect(url_for("index"))
    sesiuni = get_istoric(session["username"])
    return render_template("istoric.html",
                         sesiuni=sesiuni,
                         username=session["username"])

@app.route("/camera")
def camera():
    if "username" not in session:
        return redirect(url_for("index"))
    return render_template("camera.html", username=session["username"])

@app.route("/video_feed")
@app.route("/video_feed/<dans_context>")
def video_feed(dans_context=None):
    if not CAMERA_DISPONIBILA:
        return "Camera nu este disponibila", 503
    return Response(
        genereaza_frames(dans_context),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route("/logout")
def logout():
    username = session.get("username", "")
    session.clear()
    return render_template("logout.html", username=username)

feedback_curent = {}

@app.route("/feedback/<dans_context>")
def get_feedback(dans_context):
    from flask import jsonify
    from camera import genereaza_feedback

    # Returnam feedback generic fara a deschide camera
    feedback = {
        "mesaj": "Camera activa --- executa miscarea!",
        "tip": "info",
        "scor": 0,
        "detalii": []
    }
    return jsonify(feedback)
    
if __name__ == "__main__":
    initializare()
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)