### Network:

Crie três networks com docker:

client01 (INTFC1)
client02 (INTFC2)
server01 (INTFS1)

Altere o id das interfaces no arquivo experiment.py. Linhas 23, 24 e 25 respectivamente.

### Buildar Continainers:

Crie a imagem que será utilizada para levantar os componentes da rede;

$ docker build -t client .

### Executando programa:

Instale o influxdb como root:

$ sudo pip install influxdb

Inicie o programa:

$ sudo python3 experiment.py

### Habilitando a priorização:

$ sudo kill -s sigterm <PID>

obs: O pid do processo é printado no inicio da execução.

 
