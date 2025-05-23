
from flask import Flask, render_template, request, redirect, url_for, flash, session
from zeep import Client
import logging.config

logging.config.dictConfig({
    'version': 1,
    'formatters': {
        'verbose': {
            'format': '[%(asctime)s] %(levelname)s:%(name)s:%(message)s'
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',  # Puedes cambiar a INFO si no quieres tanto detalle
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        }
    },
    'loggers': {
        'zeep': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': True
        }
    }
})


app = Flask(__name__)
app.secret_key = "supersecret"  # Usa una clave más segura en producción
client = Client('http://localhost:8000/?wsdl')

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":

        # LOGIN
        if "email" in request.form:
            email = request.form["email"].strip()
            login = client.service.loginUser(email)
            if login.startswith("ERROR"):
                flash("Usuario no encontrado", "danger")
            else:
                playerID = login.split("|")[0]
                session['playerID'] = playerID
                session['email'] = email
                flash("¡Bienvenido! Ya puedes generar códigos y reclamar recompensas.", "success")
            return redirect(url_for("index"))

        # GENERAR CÓDIGO
        if "generate_code" in request.form:
            if 'playerID' not in session:
                flash("Primero inicia sesión con tu correo.", "warning")
                return redirect(url_for("index"))
            playerID = session['playerID']
            code_info = client.service.generateCode(playerID)
            if code_info.startswith("ERROR"):
                flash(code_info, "warning")
            else:
                code = code_info.split("|")[0]
                flash(f"Código generado: {code}", "info")
            return redirect(url_for("index"))

        # RECLAMAR CÓDIGO
        if "claim_code" in request.form:
            if 'playerID' not in session:
                flash("Primero inicia sesión con tu correo.", "warning")
                return redirect(url_for("index"))
            code = request.form.get("code", "").strip().upper()
            if not code:
                flash("Debes ingresar un código.", "warning")
                return redirect(url_for("index"))

            playerID = session['playerID']
            valid = client.service.validateCode(playerID, code)
            if not valid.startswith("VALIDO"):
                flash(valid, "danger")
            else:
                result = client.service.claimReward(playerID, code)
                flash(result, "success")
            return redirect(url_for("index"))

    return render_template("game.html", playerID=session.get('playerID'))

@app.route("/logout")
def logout():
    session.clear()
    flash("Has cerrado sesión.", "info")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
