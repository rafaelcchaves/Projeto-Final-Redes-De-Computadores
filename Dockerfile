FROM alpine:latest

RUN apk update && apk add --no-cache \
    python3 \
    py3-pip \
    tcpdump \
    iperf \
    iperf3
    
RUN python3 -m venv /venv
RUN /venv/bin/pip install scapy
RUN /venv/bin/pip install influxdb


ENV PATH="/venv/bin:$PATH"

WORKDIR /app

RUN mkdir -p /app/data

COPY receiver-socket.py /app/receiver-socket.py
COPY sender-socket.py /app/sender-socket.py
COPY receiver.py /app/receiver.py
