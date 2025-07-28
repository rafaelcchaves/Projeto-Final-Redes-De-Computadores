from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Node, OVSSwitch
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.link import Intf
from mininet.link import TCLink, TCIntf
import sys
import threading
import subprocess
import time
import argparse
import random
import signal
import os
import csv

BANDWIDTH=10 # Mbps
PRIO=False
ENABLE=False
START=0
CSV_FILE='/tmp/latencies.csv'

def create_container(name, network, verbose = False):
    params = ["docker", "run", "--privileged", "--network", network, "-i", "--name", name, "client", "bash"]
    if verbose:
        return subprocess.Popen(params)
    return subprocess.Popen(params, stdout = subprocess.PIPE, stderr = subprocess.PIPE) 

def start_publishing(verbose = False):
    params = ["python3", "scripts/publish_to_influxdb.py"]
    if verbose:
        return subprocess.Popen(params)
    return subprocess.Popen(params, stdout = subprocess.PIPE, stderr = subprocess.PIPE) 

def docker_compose_cmd(cmd, verbose = False):
    params = ["docker", "compose"]
    cmd_list = cmd.split(' ')
    if len(cmd_list) == 1: 
        params.append(cmd)
    else:
        params += cmd_list
    if verbose:
        return subprocess.Popen(params)
    return subprocess.Popen(params, stdout = subprocess.PIPE, stderr = subprocess.PIPE) 

def exec_script(name, script):
    params = ["docker", "exec", name, "bash", script]
    process = subprocess.Popen(params, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return process
 
def exec_cmd(name, cmd, output = None, i = True, verbose=False):
    params = ["docker", "exec"]
    if i:
        params.append('-i')
    params.append(name)
    params_cmd = cmd.split(' ')
    params.extend(params_cmd)
    if output != None:
        return subprocess.Popen(params, stdout = output, stderr = subprocess.STDOUT)
    if verbose:
        return subprocess.Popen(params) 
    return subprocess.Popen(params, stdout = subprocess.PIPE, stderr = subprocess.PIPE, text=True) 

def kill(name):
    params = ["docker", "rm", "-f", name]
    return subprocess.Popen(params)

class LinuxRouter( Node ):

    def config( self, **params ):
        super( LinuxRouter, self).config( **params )
        self.cmd( 'sysctl net.ipv4.ip_forward=1' )

    def terminate( self ):
        self.cmd( 'sysctl net.ipv4.ip_forward=0' )
        super( LinuxRouter, self ).terminate()

class NetworkTopo( Topo ):
    def build( self, **_opts ):
        r1 = self.addNode('r1', cls=LinuxRouter, ip=None)
        r2 = self.addNode('r2', cls=LinuxRouter, ip=None)
        r3 = self.addNode('r3', cls=LinuxRouter, ip=None)
        r4 = self.addNode('r4', cls=LinuxRouter, ip=None)
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')
        self.addLink(r1, r3, 
                     intfName1='r1-r3', params1={'ip': '192.168.101.1/24'},
                     intfName2='r3-r1', params2={'ip': '192.168.101.2/24'},
                     )
        self.addLink(r2, r3, 
                     intfName1='r2-r3', params1={'ip': '192.168.102.1/24'},
                     intfName2='r3-r2', params2={'ip': '192.168.102.2/24'},
                     )
        self.addLink(r3, r4, 
                     intfName1='r3-r4', params1={'ip': '192.168.104.2/24'},
                     intfName2='r4-r3', params2={'ip': '192.168.104.1/24'},
                     )
        self.addLink(s1, r1,
                     intfName1='s1-r1',
                     intfName2='r1-s1', params2={'ip': '172.18.0.3/24'},
                     )
        self.addLink(s2, r2, intfName1='s2-r2',
                     intfName2='r2-s2', params2={'ip': '172.19.0.3/24'},
                     )
        self.addLink(s3, r4,
                     intfName1='s3-r4',
                     intfName2='r4-s3', params2={'ip': '172.20.0.3/24'},
                     )

def eMBBTraffic():
    print("> Iniciando Tráfego eMBB")
    exec_cmd("server1", "iperf -s -i 1")
    global PRIO
    while True:
        time.sleep(3)
        if random.randint(0, 1) or (PRIO and time.monotonic() - START > 20):
            exec_cmd(f"client2", "iperf -c 172.20.0.2 -l 12K -b 1M -t 30 -i 1 ")

def uRLLCTraffic(r1, r2, r3, r4):
    metrics_file = open(CSV_FILE, mode='w', newline='')
    metrics_file.write("latency_ms,media_movel_ms\n")
    metrics_file.flush()
    time.sleep(1)
    print("> Iniciando Tráfego uRLLC")
    receiver = exec_cmd("server1", "python3 receiver-socket.py")
    time.sleep(1)
    exec_cmd("client1", "python3 sender-socket.py")
    time.sleep(1)
    start_publishing()
    time.sleep(1)
    global PRIO
    global START
    while True:
        try:
            line = receiver.stdout.readline()
            print(line, end='')
            if line[0] == '-':
                average_latency = float(line.split(' ')[-2])
                latency = float(line.split(' ')[-8])
                metrics_file.write(f'{latency},{average_latency}\n')
                metrics_file.flush()
                if ENABLE:
                    if PRIO == False and average_latency > 5:
                        print("> Inicializando priorização:")
                        r3.cmd("tc filter add dev r3-r4 protocol ip parent 1: u32 match u8 0xb8 0xff at 1 flowid 1:10")
                        START = time.monotonic()
                        PRIO = True
        except Exception as err:
            print(err)
            break

def clean():
    print("> Finalizando Containers")
    kill("client1")
    kill("client2")
    kill("server1")
    docker_compose_cmd("kill", verbose=True)

def sigintHandler(sig, frame):
    clean()
    sys.exit(0)

def sigtermHandler(sig, frame):
    global ENABLE
    ENABLE = True
    print("> Habilitando priorização:")

def run():
    topo = NetworkTopo()
    net = Mininet( topo=topo, link=TCLink, switch=OVSSwitch, waitConnected=True )
    r1 = net.get("r1")
    r2 = net.get("r2")
    r3 = net.get("r3")
    r4 = net.get("r4")
    s1 = net.get("s1")
    s2 = net.get("s2")
    s3 = net.get("s3")
    INTFC1 = "br-1865de99a78f" 
    INTFC2 = "br-01bf21c220d0"
    INTFS1 = "br-5f04dce7f1ef"
    Intf(INTFC1, node=s1)
    Intf(INTFC2, node=s2)
    Intf(INTFS1, node=s3)
    r1.cmd('ip route add 192.168.102.0/24 via 192.168.101.2')  
    r1.cmd('ip route add 192.168.104.0/24 via 192.168.101.2')  
    r1.cmd('ip route add 172.19.0.0/24 via 192.168.101.2')
    r1.cmd('ip route add 172.20.0.0/24 via 192.168.101.2')
    r2.cmd('ip route add 192.168.101.0/24 via 192.168.102.2')  
    r2.cmd('ip route add 192.168.104.0/24 via 192.168.102.2')  
    r2.cmd('ip route add 172.18.0.0/24 via 192.168.102.2')
    r2.cmd('ip route add 172.20.0.0/24 via 192.168.102.2')
    r3.cmd('ip route add 172.18.0.0/24 via 192.168.101.1 dev r3-r1')
    r3.cmd('ip route add 172.19.0.0/24 via 192.168.102.1 dev r3-r2')
    r3.cmd('ip route add 172.20.0.0/24 via 192.168.104.1 dev r3-r4')
    r4.cmd('ip route add 192.168.101.0/24 via 192.168.104.2')  
    r4.cmd('ip route add 192.168.102.0/24 via 192.168.104.2')  
    r4.cmd('ip route add 172.18.0.0/24 via 192.168.104.2')
    r4.cmd('ip route add 172.19.0.0/24 via 192.168.104.2')
    net.start()
    try:
        print("> Inicializando Containers")
        create_container("client1", "client01")
        create_container("client2", "client02")
        create_container("server1", "server01")
        docker_compose_cmd("up -d")
        time.sleep(1)
        print("> Criando rotas")
        exec_cmd("client1", 'ip route add 192.168.102.0/24 via 172.18.0.3')
        exec_cmd("client1", 'ip route add 192.168.104.0/24 via 172.18.0.3')
        exec_cmd("client1", 'ip route add 172.19.0.0/24 via 172.18.0.3')
        exec_cmd("client1", 'ip route add 172.20.0.0/24 via 172.18.0.3')
        exec_cmd("client2", 'ip route add 192.168.101.0/24 via 172.19.0.3')
        exec_cmd("client2", 'ip route add 192.168.104.0/24 via 172.19.0.3')
        exec_cmd("client2", 'ip route add 172.18.0.0/24 via 172.19.0.3')
        exec_cmd("client2", 'ip route add 172.20.0.0/24 via 172.19.0.3')
        exec_cmd("server1", 'ip route add 192.168.101.0/24 via 172.20.0.3')
        exec_cmd("server1", 'ip route add 192.168.102.0/24 via 172.20.0.3')
        exec_cmd("server1", 'ip route add 172.18.0.0/24 via 172.20.0.3')
        exec_cmd("server1", 'ip route add 172.19.0.0/24 via 172.20.0.3')

        print("> Criando regras de controle da rede")
        r3.cmd("tc qdisc add dev r3-r4 root handle 1: htb default 20")
        r3.cmd("tc class add dev r3-r4 parent 1: classid 1:1 htb rate 10mbit ceil 10mbit")
        r3.cmd("tc class add dev r3-r4 parent 1:1 classid 1:10 htb rate 1mbit ceil 10mbit prio 1")
        r3.cmd("tc class add dev r3-r4 parent 1:1 classid 1:20 htb rate 9mbit ceil 10mbit prio 2")

        embb = threading.Thread(target = eMBBTraffic)
        embb.daemon = True
        urllc = threading.Thread(target = uRLLCTraffic, args = (r1, r2, r3, r4))
        urllc.daemon = True

        embb.start()
        urllc.start()

        urllc.join()

    except Exception as err:
        print("> Encerrando execução devido ao seguinte erro: ")
        print(err)

    clean()
    net.stop()

if __name__ == '__main__':
    signal.signal(signal.SIGINT, sigintHandler) 
    signal.signal(signal.SIGTERM, sigtermHandler) 
    run()
