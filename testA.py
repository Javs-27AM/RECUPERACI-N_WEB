from zeep import Client
from datetime import datetime

client = Client('http://localhost:8000/?wsdl')

# Paso 1: Login
email = "testa@example.com"
login_response = client.service.loginUser(email)
assert not login_response.startswith("ERROR"), "El jugador no existe"
player_id = login_response.split("|")[0]

# Paso 2: Generar código
code_response = client.service.generateCode(player_id)
assert not code_response.startswith("ERROR"), "No se pudo generar el código"
code = code_response.split("|")[0]

# Paso 3: Validar el código
valid_response = client.service.validateCode(player_id, code)
assert valid_response == "VALIDO", f"Código inválido: {valid_response}"

# Paso 4: Reclamar la recompensa
reward_response = client.service.claimReward(player_id, code)
assert reward_response.startswith("Día"), f"Error al reclamar: {reward_response}"

print("[✓] Test a: Canje y reclamo exitoso ->", reward_response)
