import time
import csv
from influxdb import InfluxDBClient
import os

# Configurações do InfluxDB local
INFLUXDB_HOST = "localhost"
INFLUXDB_PORT = 8086
INFLUXDB_DATABASE = "metric_topology_db"

# Configurações do CSV e Leitura
CSV_FILE_PATH = "/tmp/latencies.csv"
READ_INTERVAL_SECONDS = 2

# Variável para manter o controle da posição lida no arquivo
last_read_position = 0

def read_and_publish_csv():
    global last_read_position

    # Inicializa o cliente InfluxDB
    client = InfluxDBClient(host=INFLUXDB_HOST, port=INFLUXDB_PORT)
    client.switch_database(INFLUXDB_DATABASE)

    print(f"[*] Monitorando {CSV_FILE_PATH} para novas entradas...")

    while True:
        try:
            # Verifica se o arquivo existe e tem conteúdo
            if not os.path.exists(CSV_FILE_PATH) or os.path.getsize(CSV_FILE_PATH) == 0:
                print(f"[!] Arquivo CSV '{CSV_FILE_PATH}' não encontrado ou vazio. Aguardando...")
                last_read_position = 0
                time.sleep(READ_INTERVAL_SECONDS)
                continue

            # Abre o arquivo para leitura, a partir da última posição lida
            with open(CSV_FILE_PATH, 'r') as file:
                file.seek(last_read_position)

                reader = csv.reader(file)

                # Se for a primeira vez lendo, pule o cabeçalho
                if last_read_position == 0:
                    try:
                        header = next(reader)
                        print(f"[*] CSV Header: {header}")
                    except StopIteration:
                        print("[!] CSV está vazio exceto pelo cabeçalho. Aguardando dados...")
                        time.sleep(READ_INTERVAL_SECONDS)
                        continue

                new_data_found = False
                for row in reader:
                    if len(row) == 2:
                        try:
                            latency_value = float(row[0])
                            moving_avg_value = float(row[1])

                            # Formata o dado no formato esperado pelo InfluxDB 1.8
                            json_body = [{
                                "measurement": "latency",
                                "tags": {
                                    "host": "topo01"
                                },
                                "fields": {
                                    "latency_ms": latency_value,
                                    "moving_avg_ms": moving_avg_value
                                }
                            }]

                            client.write_points(json_body)
                            print(f"[+] Publicado: Latência={latency_value:.2f}ms, Média={moving_avg_value:.2f}ms")
                            new_data_found = True

                        except ValueError as ve:
                            print(f"[!] Erro ao converter dados para float: {row}. Erro: {ve}")
                        except Exception as e:
                            print(f"[!] Erro ao escrever no InfluxDB: {e}")
                    else:
                        print(f"[!] Linha inesperada no CSV (esperado 2 colunas): {row}")

                # Atualiza a posição
                last_read_position = file.tell()

                if not new_data_found:
                    print("[*] Nenhuma nova linha. Aguardando...")

            time.sleep(READ_INTERVAL_SECONDS)

        except FileNotFoundError:
            print(f"[!] Arquivo '{CSV_FILE_PATH}' não encontrado. Aguardando...")
            last_read_position = 0
            time.sleep(READ_INTERVAL_SECONDS)
        except Exception as e:
            print(f"[!!!] Erro fatal no monitoramento do CSV: {e}")
            time.sleep(READ_INTERVAL_SECONDS * 2)

if __name__ == "__main__":
    read_and_publish_csv()
