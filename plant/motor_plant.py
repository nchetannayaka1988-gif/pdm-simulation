# plant/motor_plant.py
import numpy as np
import pandas as pd
import json
from enum import Enum
from dataclasses import dataclass

class Fault(Enum):
    HEALTHY = 0
    INNER_RACE = 1
    OUTER_RACE = 2

@dataclass
class Params:
    rpm: float = 1800.0
    n_balls: int = 9
    ball_dia: float = 7.938e-3
    pitch_dia: float = 38.5e-3
    fs: int = 10000          # 10 ksps
    packet_ms: int = 100     # 100ms packets
    duration: int = 60       # seconds per scenario

class MotorSim:
    def __init__(self, p: Params):
        self.p = p
        self.bpfi = p.n_balls * p.rpm/120 * (1 + p.ball_dia/p.pitch_dia)
        self.bpfo = p.n_balls * p.rpm/120 * (1 - p.ball_dia/p.pitch_dia)
        self.dt = 1.0 / p.fs
        self.samples_per_packet = int(p.packet_ms * p.fs / 1000)
        
    def _impulse(self, t):
        fn, zeta = 3500, 0.05
        wd = 2*np.pi*fn*np.sqrt(1-zeta**2)
        return np.exp(-zeta*2*np.pi*fn*t) * np.sin(wd*t)
    
    def generate(self, fault: Fault, severity=0.3):
        packets = []
        vib_buffer = np.zeros(self.samples_per_packet)
        
        for pkt_idx in range(self.p.duration * 1000 // self.p.packet_ms):
            # Fill vibration buffer
            for i in range(self.samples_per_packet):
                t = (pkt_idx * self.samples_per_packet + i) * self.dt
                f_rot = self.p.rpm / 60
                vib = 0.5*np.sin(2*np.pi*f_rot*t) + 0.2*np.sin(4*np.pi*f_rot*t)  # 1x, 2x RPM
                vib += np.random.normal(0, 0.1)
                
                if fault != Fault.HEALTHY:
                    f_fault = self.bpfi if fault == Fault.INNER_RACE else self.bpfo
                    period = 1.0 / f_fault
                    t_mod = t % period
                    if t_mod < 0.001:
                        vib += severity * 10 * self._impulse(t_mod)
                
                vib_buffer[i] = vib
            
            # FFT (512 bins)
            fft = np.fft.rfft(vib_buffer, n=512)
            mag = np.abs(fft)[:512].tolist()
            
            # Current RMS (simplified)
            curr_rms = 5.0 + np.random.normal(0, 0.1)
            temp = 45.0 + np.random.normal(0, 0.5)
            
            packets.append({
                'timestamp': pkt_idx * self.p.packet_ms / 1000.0,
                'vibration_spectrum': json.dumps(mag),
                'current_rms': curr_rms,
                'temperature': temp,
                'rpm': self.p.rpm,
                'fault_label': fault.value,
                'fault_severity': severity
            })
        return packets

def main():
    p = Params()
    sim = MotorSim(p)
    for fault in Fault:
        name = fault.name.lower()
        packets = sim.generate(fault)
        df = pd.DataFrame(packets)
        df.to_csv(f"data/{name}.csv", index=False)
        print(f"Generated data/{name}.csv: {len(df)} rows")

if __name__ == "__main__":
    main()