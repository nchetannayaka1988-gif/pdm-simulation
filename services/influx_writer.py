# services/influx_writer.py
import json
import os
import numpy as np
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point, WriteOptions

INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "my-super-secret-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "pdm")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "pdm-data")

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=WriteOptions(batch_size=100, flush_interval=1000))

def on_connect(client, userdata, flags, rc, properties=None):
    print(f"MQTT Connected (rc={rc})")
    if rc == 0:
        client.subscribe("pdm/gateway/plc/data")
        print("Subscribed to pdm/gateway/plc/data")
    else:
        print(f"Connection failed: {rc}")

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        vib = np.array(data.get("vib", []))
        
        point = Point("plc_data") \
            .tag("source", "plc_sim") \
            .field("current_rms", float(data.get("curr", 0))) \
            .field("temperature", float(data.get("temp", 0))) \
            .field("rpm", float(data.get("rpm", 1800))) \
            .field("fault", int(data.get("fault", 0)))
        
        if len(vib) > 0:
            point.field("vib_rms", float(np.sqrt(np.mean(vib**2))))
            point.field("vib_peak", float(np.max(np.abs(vib))))
            bpfi_idx = int(156 * 512 / 5000)
            bpfo_idx = int(107 * 512 / 5000)
            point.field("bpfi_energy", float(np.sum(vib[max(0,bpfi_idx-2):bpfi_idx+3]**2)))
            point.field("bpfo_energy", float(np.sum(vib[max(0,bpfo_idx-2):bpfo_idx+3]**2)))
        
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
        print(f"Written: ts={data.get('ts')}, fault={data.get('fault')}, vib_rms={point._fields.get('vib_rms')}")
    except Exception as e:
        print(f"Write error: {e}")

# Use MQTT v5 API (callback_api_version=2)
mqtt_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

print("Connecting to MQTT broker...")
mqtt_client.connect("mqtt", 1883, 60)
print("Starting loop...")
mqtt_client.loop_forever()