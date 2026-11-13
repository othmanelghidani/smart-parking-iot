"""Serial <-> MQTT gateway for the Smart Parking system.

Reads the Arduino telemetry line over USB serial, converts it to JSON and
publishes it on MQTT for the Node-RED dashboard. Commands received from
Node-RED (OPEN / CLOSE) are forwarded to the Arduino.

Configuration comes from environment variables (see .env.example).
"""

import json
import os
import uuid

import serial
import paho.mqtt.client as mqtt

MQTT_BROKER = os.getenv("MQTT_BROKER", "broker.hivemq.com")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

# Unique topic prefix: on a public broker, anyone who knows it can read the
# telemetry and send commands, so keep your own value private.
TOPIC_PREFIX = os.getenv("MQTT_TOPIC_PREFIX") or str(uuid.uuid4())

TELEMETRY_TOPIC = f"{TOPIC_PREFIX}/telemetry"
COMMAND_TOPIC = f"{TOPIC_PREFIX}/commands"

SERIAL_PORT = os.getenv("SERIAL_PORT", "COM3")
BAUD_RATE = int(os.getenv("BAUD_RATE", "9600"))

ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker")
    client.subscribe(COMMAND_TOPIC)
    print("Subscribed to:", COMMAND_TOPIC)

def on_message(client, userdata, msg):
    command = msg.payload.decode().strip()
    print("Command received from Node-RED:", command)

    ser.write((command + "\n").encode())
    print("Command sent to Arduino:", command)

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()

print("Gateway started")
print("MQTT topic prefix:", TOPIC_PREFIX)
print("Reading Arduino from:", SERIAL_PORT)

while True:
    line = ser.readline().decode(errors="ignore").strip()

    if not line:
        continue

    print("Arduino:", line)

    if line.startswith("ACK"):
        continue

    parts = line.split(",")

    if len(parts) < 4:
        continue

    try:
        payload = {
            "distance": int(parts[0]),
            "rfidStatus": parts[1],
            "parkingStatus": parts[2],
            "barrierStatus": parts[3],
            "lastCardUID": parts[4] if len(parts) > 4 else "NONE",
            "lastInvalidUID": parts[5] if len(parts) > 5 else "NONE"
        }

        client.publish(TELEMETRY_TOPIC, json.dumps(payload))
        print("Sent to Node-RED:", payload)

    except ValueError:
        continue