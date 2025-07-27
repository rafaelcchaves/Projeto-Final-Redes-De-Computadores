import socket
import time
import sys
from collections import deque


IP = "0.0.0.0"
PORT = 5005
BUFFER_SIZE = 1024
MOVING_WINDOW_SIZE = 20
latencies = deque(maxlen=MOVING_WINDOW_SIZE)
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 10485760)
server.bind((IP, PORT))
server.listen(1)


print("[*] Aguardando conexão TCP na porta {PORT}...")
sys.stdout.flush()
conn, addr = server.accept()
print(f"[+] Conectado por {addr}")
sys.stdout.flush()

buffer = ""

while True:
    try:
        sys.stdout.flush()
        data = conn.recv(BUFFER_SIZE)
        if not data:
            break
        now = time.time()
        buffer += data.decode()
        init = buffer.find('|')
        end = buffer.find('|', init + 1)
        if init == -1 or end == -1:
            continue
        message = buffer[init+1:end]
        buffer = buffer[end+1:]
        sent_time, seq = message.split(',')
        sent_time = float(sent_time)
        latency_ms = (now - sent_time) * 1000
        latencies.append(latency_ms)
        avg = sum(latencies) / len(latencies)
        print(f"[{addr[0]}] Seq: {seq} | Latência: {latency_ms:.2f} ms | Média móvel ({len(latencies)}): {avg:.2f} ms")
        sys.stdout.flush()
    except Exception as e:
        print(f"[!] Erro ao processar pacote: {e}")
        sys.stdout.flush()
        break

conn.close()
