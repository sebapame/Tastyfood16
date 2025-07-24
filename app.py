from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
from pytz import timezone
from sqlalchemy import create_engine, text
import pandas as pd
import os

app = Flask(__name__)
tz = timezone("America/Santiago")

# URL de la base de datos PostgreSQL
DATABASE_URL = "postgresql://estacionamiento2_db_user:0AoObGxcyxxb1gJkQGcNkXTG81J4kGVi@dpg-d20081fdiees73c3gv2g-a/estacionamiento2_db"
engine = create_engine(DATABASE_URL)

# Crear la tabla si no existe
def init_db():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS registros (
                id SERIAL PRIMARY KEY,
                patente TEXT,
                hora_entrada TEXT,
                hora_salida TEXT,
                monto INTEGER,
                medio_pago TEXT
            )
        """))

# Ejecutar una vez al iniciar
init_db()

def get_time_now():
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

@app.route("/", methods=["GET", "POST"])
def index():
    mensaje = ""
    filtro_fecha = request.args.get("fecha", datetime.now(tz).strftime("%Y-%m-%d"))
    mostrar_monto = False
    minutos = 0
    monto = 0
    datos_salida = {}

    if request.method == "POST":
        patente = request.form["patente"].upper()
        now = get_time_now()
        medio_pago = request.form.get("medio_pago", "")

        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM registros WHERE patente = :pat AND hora_salida IS NULL"), {"pat": patente})
            registro = result.fetchone()

            if registro:
                # Es una salida
                hora_entrada = datetime.strptime(registro[2], "%Y-%m-%d %H:%M:%S")
                hora_salida = datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
                minutos_original = int((hora_salida - hora_entrada).total_seconds() / 60)
                minutos = round(minutos_original / 10) * 10
                monto = 500 if minutos <= 15 else 500 + (minutos - 15) * 24

                if medio_pago:
                    conn.execute(text("""
                        UPDATE registros
                        SET hora_salida = :salida, monto = :monto, medio_pago = :pago
                        WHERE id = :id
                    """), {
                        "salida": now,
                        "monto": monto,
                        "pago": medio_pago,
                        "id": registro[0]
                    })
                    return redirect(url_for("index", fecha=filtro_fecha))
                else:
                    mostrar_monto = True
                    datos_salida = {
                        "patente": patente,
                        "minutos": minutos,
                        "monto": monto
                    }
            else:
                # Es una entrada
                conn.execute(text("INSERT INTO registros (patente, hora_entrada) VALUES (:pat, :entrada)"),
                             {"pat": patente, "entrada": now})
                return redirect(url_for("index", fecha=filtro_fecha))

    with engine.connect() as conn:
        df = pd.read_sql_query(
            "SELECT * FROM registros WHERE DATE(hora_entrada) = :fecha ORDER BY id DESC",
            conn,
            params={"fecha": filtro_fecha}
        )

    return render_template("index.html",
                           registros=df.iterrows(),
                           fecha=filtro_fecha,
                           mostrar_monto=mostrar_monto,
                           datos_salida=datos_salida)

if __name__ == "__main__":
    app.run(debug=True)
