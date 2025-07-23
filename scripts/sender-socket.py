import socket
import time

DEST_IP = "172.20.0.2"
DEST_PORT = 5005
TOS_URRLC = 0xb8  #DSCP EF (Expedited Forwarding)
INTERVAL = 0.2

#Cria socket TCP
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

#Define o campo TOS antes de conectar
sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, TOS_URRLC)

#Conecta ao servidor
sock.connect((DEST_IP, DEST_PORT))
print(f"[+] Conectado a {DEST_IP}:{DEST_PORT} com TOS {hex(TOS_URRLC)}")

#Envia timestamps como payload
while True:
    try:
        timestamp = str(time.time()).encode()
        sock.sendall(timestamp)
        print(f"[>] URLLC enviado com timestamp {timestamp.decode()}")
        time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print("\n[!] Encerrando envio")
        break

sock.close()
