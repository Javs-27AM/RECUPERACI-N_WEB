import random, string
from datetime import datetime, timedelta, date
from spyne import Application, rpc, ServiceBase, Unicode
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
import psycopg2


# Conexión a PostgreSQL
conn = psycopg2.connect(
    dbname="rewards",
    user="postgres",
    password="1234",
    host="localhost",
    port="5432"
)
conn.autocommit = True

def base36_to_int(s):
    return int(s, 36)

def generar_codigo_no_seriable(ultimo_codigo):
    max_intentos = 10
    letras = ''.join(random.choices(string.ascii_uppercase, k=3))

    ultimo_num = None
    if ultimo_codigo:
        # Extraemos la parte alfanumérica (después del guion)
        ultimo_num = base36_to_int(ultimo_codigo.split('-')[1])

    for _ in range(max_intentos):
        alfanum = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        nuevo_num = base36_to_int(alfanum)

        # Verifica que no sea consecutivo ni igual
        if ultimo_num is not None:
            if abs(nuevo_num - ultimo_num) <= 1:
                continue  # Código seriable, probar otro
        nuevo_codigo = f"{letras}-{alfanum}"

        # Verificar que no exista en BD
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM tokens WHERE code=%s", (nuevo_codigo,))
            if cur.fetchone():
                continue  # Código ya existe, generar otro
        return nuevo_codigo


REWARDS = {
    d: f"Recompensa del día {d}" for d in range(1, 29)
}
REWARDS[28] = "Recompensa final: cofre legendario"

class RewardService(ServiceBase):

    @rpc(Unicode, _returns=Unicode)
    def loginUser(ctx, email):
        with conn.cursor() as cur:
            cur.execute("SELECT player_id, client_id FROM users WHERE email=%s", (email,))
            user = cur.fetchone()
            if not user:
                return "ERROR|Usuario no encontrado"
            return f"{user[0]}|{user[1]}"

    @rpc(Unicode, _returns=Unicode)
    def generateCode(ctx, playerID):
        today = date.today()
        with conn.cursor() as cur:
            # Verifica si ya generó código hoy
            cur.execute("SELECT code FROM tokens WHERE player_id=%s AND date_generated=%s", (playerID, today))
            if cur.fetchone():
                return "ERROR|Código ya generado hoy"

            # Obtener día actual
            # cur.execute("SELECT current_day FROM player_progress WHERE player_id=%s", (playerID,))
            # row = cur.fetchone()
            # day = row[0] + 1 if row else 1
            # Obtener día actual
            # Obtener progreso actual
            cur.execute("""
                SELECT current_day, first_request_date, last_request_date
                FROM player_progress
                WHERE player_id=%s
            """, (playerID,))
            row = cur.fetchone()

            if row:
                current_day, first_date, last_date = row
                # Verificar si es día consecutivo
                if last_date and (today - last_date).days == 1:
                    day = current_day + 1
                elif last_date and (today - last_date).days > 1:
                    # Reinicia el progreso si hay interrupción
                    day = 1
                    first_date = today
                else:
                    # Mismo día o primer uso
                    day = current_day
            else:
                # Primer día para este jugador
                day = 1
                first_date = today
                last_date = today



            if day > 28:
                return "ERROR|Ya has completado las 28 recompensas"

            # Actualiza progreso
            # if row:
            #     cur.execute("UPDATE player_progress SET current_day=%s WHERE player_id=%s", (day, playerID))
            # else:
            #     cur.execute("INSERT INTO player_progress (player_id, current_day) VALUES (%s, %s)", (playerID, day))
            if row:
                cur.execute("""
                    UPDATE player_progress
                    SET current_day=%s, last_request_date=%s, first_request_date=%s
                    WHERE player_id=%s
                """, (day, today, first_date, playerID))
            else:
                cur.execute("""
                    INSERT INTO player_progress (player_id, current_day, first_request_date, last_request_date)
                    VALUES (%s, %s, %s, %s)
                """, (playerID, day, first_date, today))

            # Obtener el último código generado para evitar seriabilidad
            cur.execute("SELECT code FROM tokens ORDER BY date_generated DESC, expires_at DESC LIMIT 1")
            row = cur.fetchone()
            ultimo_codigo = row[0] if row else None

            # Generar código no seriable y único
            code = generar_codigo_no_seriable(ultimo_codigo)

            expires = (datetime.now() + timedelta(days=1)).replace(hour=5, minute=0, second=0, microsecond=0)

            cur.execute("""
                INSERT INTO tokens (code, player_id, expires_at, used, day, date_generated)
                VALUES (%s, %s, %s, FALSE, %s, %s)
            """, (code, playerID, expires, day, today))

            return f"{code}|{day}|{expires.strftime('%Y-%m-%d %H:%M:%S')}"

    @rpc(Unicode, Unicode, _returns=Unicode)
    def validateCode(ctx, playerID, code):
        with conn.cursor() as cur:
            cur.execute("""
                SELECT player_id, expires_at, used FROM tokens WHERE code=%s
            """, (code,))
            token = cur.fetchone()

            if not token:
                return "ERROR|Código inexistente"
            if token[0] != playerID:
                return "ERROR|Código no pertenece a este jugador"
            if datetime.now() > token[1]:
                return "ERROR|Código expirado"
            if token[2]:
                return "ERROR|Código ya usado"
            return "VALIDO"

    @rpc(Unicode, Unicode, _returns=Unicode)
    def claimReward(ctx, playerID, code):
        with conn.cursor() as cur:
            cur.execute("SELECT player_id, expires_at, used, day FROM tokens WHERE code=%s", (code,))
            token = cur.fetchone()
            if not token:
                return "ERROR|Código no válido"
            if token[2]:
                return "ERROR|Código ya fue usado"
            if token[0] != playerID:
                return "ERROR|Código no pertenece a este jugador"
            if datetime.now() > token[1]:
                return "ERROR|Código expirado"

            # Marcar como usado
            cur.execute("UPDATE tokens SET used=TRUE WHERE code=%s", (code,))
            reward = REWARDS.get(token[3], "Recompensa por definir")
            return f"Día {token[3]}: {reward}"

# App SOAP
application = Application(
    [RewardService],
    tns='rewards',
    in_protocol=Soap11(validator='lxml'),
    out_protocol=Soap11()
)

if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    print("Servidor SOAP en http://localhost:8000")
    server = make_server('0.0.0.0', 8000, WsgiApplication(application))
    server.serve_forever()
