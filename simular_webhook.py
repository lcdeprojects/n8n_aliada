import urllib.request
import urllib.error
import json
import ssl

# Define a URL do seu servidor local Django
url = ''

# Cria o corpo da requisição exatamente como o Chatwoot enviaria
# Você pode alterar o "phone_number" e o "name" abaixo para o seu!
payload = {
    "event": "contact_created",
    "meta": {
        "sender": {
            "id": 9999,
            "name": "Seu Nome de Teste",
            "phone_number": "+5511999999999" # <-- Coloque seu número aqui para testar
        }
    }
}

data = json.dumps(payload).encode('utf-8')
headers = {'Content-Type': 'application/json'}

print(f"Enviando Webhook Simulado para {url}...")
print(f"Dados: {json.dumps(payload, indent=2)}")

# Fazendo a requisição
req = urllib.request.Request(url, data=data, headers=headers, method='POST')

try:
    # Ignora verificação SSL se estiver local (não afeta o django local, mas é boa prática)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    with urllib.request.urlopen(req, context=ctx) as response:
        print(f"\n✅ SUCESSO! Código de Resposta: {response.status}")
        print("Resposta do Django:", response.read().decode('utf-8'))
        print("\nVerifique o seu Painel (Kanban) do Django agora. O paciente já deve estar lá!")
        
except urllib.error.URLError as e:
    print(f"\n❌ ERRO AO CONECTAR!")
    if hasattr(e, 'code'):
        print(f"Código do Erro: {e.code}")
    if hasattr(e, 'reason'):
        print(f"Motivo: {e.reason}")
    print("\nDica: Verifique se o seu servidor Django está rodando com 'python manage.py runserver'")
