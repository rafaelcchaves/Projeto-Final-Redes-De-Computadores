from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Node, OVSSwitch
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.link import Intf
from mininet.link import TCLink, TCIntf
import subprocess
import time
import argparse

def create_container(name, network, verbose = False):
    params = ["docker", "run", "--privileged", "--network", network, "-i", "--name", name, "client", "bash"]
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
    return subprocess.Popen(params, stdout = subprocess.PIPE, stderr = subprocess.PIPE) 

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
                     intfName2='r3-r1', params2={'ip': '192.168.101.2/24'}, use_tbf=True)
        self.addLink(s1, r1, intfName1='s1-r1', intfName2='r1-s1', params2={'ip': '172.18.0.3/24'})
        self.addLink(r2, r3, 
                     intfName1='r2-r3', params1={'ip': '192.168.102.1/24'},
                     intfName2='r3-r2', params2={'ip': '192.168.102.2/24'}, use_tbf=True)
        self.addLink(s2, r2, intfName1='s2-r2', intfName2='r2-s2', params2={'ip': '172.19.0.3/24'})
        self.addLink(r3, r4, 
                     intfName1='r3-r4', params1={'ip': '192.168.104.2/24'},
                     intfName2='r4-r3', params2={'ip': '192.168.104.1/24'}, use_tbf=True)
        self.addLink(s3, r4, intfName1='s3-r4', intfName2='r4-s3', params2={'ip': '172.20.0.3/24'})

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
        print("Inicializando Containers")
        create_container("client1", "client01")
        create_container("client2", "client02")
        create_container("server1", "server01")
        time.sleep(1)
        print("Criando rotas")
        exec_cmd("client1", 'ip route add 192.168.102.0/24 via 172.18.0.3', verbose=True).wait()
        exec_cmd("client1", 'ip route add 192.168.104.0/24 via 172.18.0.3', verbose=True).wait()
        exec_cmd("client1", 'ip route add 172.19.0.0/24 via 172.18.0.3', verbose=True).wait()
        exec_cmd("client1", 'ip route add 172.20.0.0/24 via 172.18.0.3', verbose=True).wait()
        exec_cmd("client2", 'ip route add 192.168.101.0/24 via 172.19.0.3', verbose=True).wait()
        exec_cmd("client2", 'ip route add 192.168.104.0/24 via 172.19.0.3', verbose=True).wait()
        exec_cmd("client2", 'ip route add 172.18.0.0/24 via 172.19.0.3', verbose=True).wait()
        exec_cmd("client2", 'ip route add 172.20.0.0/24 via 172.19.0.3', verbose=True).wait()
        exec_cmd("server1", 'ip route add 192.168.101.0/24 via 172.20.0.3', verbose=True).wait()
        exec_cmd("server1", 'ip route add 192.168.102.0/24 via 172.20.0.3', verbose=True).wait()
        exec_cmd("server1", 'ip route add 172.18.0.0/24 via 172.20.0.3', verbose=True).wait()
        exec_cmd("server1", 'ip route add 172.19.0.0/24 via 172.20.0.3', verbose=True).wait()

    except Exception as err:
        print(err)
    finally:
        print("Finalizando Containers")
        kill("client1")
        kill("client2")
        kill("server1")
    net.stop()

if __name__ == '__main__':
    run()
