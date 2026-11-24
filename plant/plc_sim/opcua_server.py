# plc_sim/opcua_server.py
import asyncio, json, itertools
from asyncua import Server
import pandas as pd
import paho.mqtt.client as mqtt

class PLCSim:
    def __init__(self):
        self.server = Server()
        self.server.set_endpoint("opc.tcp://0.0.0.0:4840/freeopcua/server/")
        self.dfs = {
            'healthy': pd.read_csv('../data/healthy.csv'),
            'inner_race': pd.read_csv('../data/inner_race.csv'),
            'outer_race': pd.read_csv('../data/outer_race.csv')
        }
        self.cycle = itertools.cycle(['healthy', 'inner_race', 'outer_race'])
        self.mqtt = mqtt.Client()
        self.mqtt.connect("mqtt", 1883)
        self.mqtt.loop_start()
        
    async def setup(self):
        await self.server.init()
        idx = await self.server.register_namespace("urn:pdm-gateway:plc")
        obj = await self.server.nodes.objects.add_object(idx, "PLC_Sim")
        self.vib = await obj.add_variable(idx, "VibrationSpectrum", [0.0]*512)
        self.curr = await obj.add_variable(idx, "CurrentRMS", 0.0)
        self.temp = await obj.add_variable(idx, "Temperature", 0.0)
        await self.vib.set_writable(); await self.curr.set_writable(); await self.temp.set_writable()
        
    async def run(self):
        await self.setup()
        print("OPC UA: opc.tcp://0.0.0.0:4840/freeopcua/server/")
        async with self.server:
            while True:
                scenario = next(self.cycle)
                df = self.dfs[scenario]
                for _, row in df.iterrows():
                    vib = json.loads(row['vibration_spectrum'])
                    await self.vib.write_value(vib)
                    await self.curr.write_value(float(row['current_rms']))
                    await self.temp.write_value(float(row['temperature']))
                    self.mqtt.publish("pdm/gateway/plc/data", json.dumps({
                        'ts': row['timestamp'], 'vib': vib, 'curr': row['current_rms'],
                        'temp': row['temperature'], 'rpm': row['rpm'], 'fault': row['fault_label']
                    }))
                    await asyncio.sleep(0.1)

if __name__ == "__main__":
    asyncio.run(PLCSim().run())