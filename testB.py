from zeep import Client
import psycopg2
from datetime import datetime, timedelta

client = Client('http://localhost:8000/?wsdl')

# Login
email = "testb@example.com"
login_response = client.service.loginUser(email)
player_id = login_response.split("|")[0]

# Generar código
code_response = client.service.generateCode(player_id)
code = code_response.split("|")[0]

# Simular que ya es después de la expiración
conn = psycopg2.connect(
    dbname="rewards",
    user="postgres",
    password="1234",
    host="localhost",
    port="5432"
)
with conn:
    with conn.cursor() as cur:
        cur.execute("UPDATE tokens SET expires_at=%s WHERE code=%s",
                    ((datetime.now() - timedelta(hours=6)).strftime('%Y-%m-%d %H:%M:%S'), code))

# Intentar validar y reclamar
valid_response = client.service.validateCode(player_id, code)
assert valid_response == "ERROR|Código expirado", f"Resultado inesperado: {valid_response}"

claim_response = client.service.claimReward(player_id, code)
assert claim_response == "ERROR|Código expirado", f"Resultado inesperado: {claim_response}"

print("[✓] Test b: Intento de canje post-expiración fallido correctamente")
