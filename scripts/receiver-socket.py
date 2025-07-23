import socket
import time
from collections import deque

IP = "0.0.0.0"
PORT = 5005
BUFFER_SIZE = 1024
MOVING_WINDOW_SIZE = 10
latencies = deque(maxlen=MOVING_WINDOW_SIZE)

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((IP, PORT))
server.listen(1)

print(f"[*] Aguardando conexão TCP na porta {PORT}...")
conn, addr = server.accept()
print(f"[+] Conectado por {addr}")

while True:
    try:
        data = conn.recv(BUFFER_SIZE)
        if not data:
            break
        sent_time = float(data.decode())
        now = time.time()
        latency_ms = (now - sent_time) * 1000
        latencies.append(latency_ms)
        avg = sum(latencies) / len(latencies)
        print(f"[{addr[0]}] Latência: {latency_ms:.2f} ms | Média móvel ({len(latencies)}): {avg:.2f} ms")
    except Exception as e:
        print(f"[!] Erro ao processar pacote: {e}")
        break

conn.close()
