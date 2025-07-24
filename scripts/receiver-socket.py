import socket
import time
import sys
from collections import deque


IP = "0.0.0.0"
PORT = 5005
BUFFER_SIZE = 1024
MOVING_WINDOW_SIZE = 10
latencies = deque(maxlen=MOVING_WINDOW_SIZE)
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((IP, PORT))
server.listen(1)

print("[*] Aguardando conexão TCP na porta {PORT}...")
sys.stdout.flush()
conn, addr = server.accept()
print(f"[+] Conectado por {addr}")

while True:
    try:
        sys.stdout.flush()
        data = conn.recv(1300)
        if not data:
            break
        raw = data.decode()
        init = raw.find('|')
        end = raw.find('|', init + 1)
        message = raw[init+1:end]
        sent_time, seq = message.split(',')
        sent_time = float(sent_time)
        now = time.time()
        latency_ms = (now - sent_time) * 1000
        latencies.append(latency_ms)
        if len(latencies) > 10:
            latencies.pop(0)
        avg = sum(latencies) / len(latencies)
        print(f"[{addr[0]}] Seq: {seq} | Latência: {latency_ms:.2f} ms | Média móvel ({len(latencies)}): {avg:.2f} ms")
        sys.stdout.flush()
    except Exception as e:
        print(f"[!] Erro ao processar pacote: {e}")
        sys.stdout.flush()
        break

conn.close()
