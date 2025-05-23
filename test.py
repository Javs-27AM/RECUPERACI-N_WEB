# test_rewards.py
from zeep import Client
from datetime import datetime, timedelta
import time

client = Client('http://localhost:8000/?wsdl')

def test_a_claim_valid_token():
    print("Prueba A: Reclamar token válido")

    email = "testt@example.com" 
    login = client.service.loginUser(email)
    assert not login.startswith("ERROR"), "Login fallido"

    playerID = login.split("|")[0]

    # Generar código
    code_info = client.service.generateCode(playerID)
    assert not code_info.startswith("ERROR"), "Generación de código fallida"
    
    code = code_info.split("|")[0]

    # Validar código
    validacion = client.service.validateCode(playerID, code)
    assert validacion == "VALIDO", f"Código inválido: {validacion}"

    # Reclamar recompensa
    recompensa = client.service.claimReward(playerID, code)
    assert "Día" in recompensa, f"Fallo en recompensa: {recompensa}"
    print("✔ Test A pasado:", recompensa)

def test_b_token_expired():
    print("Prueba B: Código válido pero expirado")

    email = "testt@example.com"  
    login = client.service.loginUser(email)
    assert not login.startswith("ERROR"), "Login fallido"

    playerID = login.split("|")[0]

    # Generar código
    code_info = client.service.generateCode(playerID)
    assert not code_info.startswith("ERROR"), "Generación fallida"

    code = code_info.split("|")[0]
    print("⏳ Esperando simulación de expiración...")

    from psycopg2 import connect
    conn = connect(
        dbname="rewards",
        user="postgres",
        password="1234",
        host="localhost",
        port="5432"
    )
    with conn.cursor() as cur:
        cur.execute("UPDATE tokens SET expires_at = %s WHERE code = %s", (datetime.now() - timedelta(hours=1), code))
        conn.commit()

    # Intentar reclamar
    respuesta = client.service.claimReward(playerID, code)
    assert respuesta == "ERROR|Código expirado", f"Esperado código expirado, obtenido: {respuesta}"
    print("✔ Test B pasado: Código correctamente expirado")

if __name__ == "__main__":
    test_a_claim_valid_token()
    test_b_token_expired()
