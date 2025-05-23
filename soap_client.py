from zeep import Client

# Crear cliente SOAP
client = Client('http://localhost:8000/?wsdl')

# Llamadas a métodos del servicio
email = "antonio@example.com"
login_result = client.service.loginUser(email)
print("Login:", login_result)

playerID = login_result.split('|')[0]
code_info = client.service.generateCode(playerID)
print("Código generado:", code_info)

# Validar código
code = code_info.split('|')[0]
valid = client.service.validateCode(playerID, code)
print("Validación:", valid)

# Reclamar recompensa
if valid == "VALIDO":
    reward = client.service.claimReward(playerID, code)
    print("Recompensa:", reward)
