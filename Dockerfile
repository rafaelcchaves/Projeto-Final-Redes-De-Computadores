FROM ubuntu:22.04

RUN apt update && apt install -y \
    python3 \
    python3-pip \
    tcpdump \
    iputils-ping \ 
    iproute2 \
    iperf \
    iperf3 \
    traceroute
    
RUN pip install scapy
RUN pip install influxdb

WORKDIR /app

RUN mkdir -p /app/data

COPY scripts/receiver-socket.py /app/receiver-socket.py
COPY scripts/sender-socket.py /app/sender-socket.py
