import os
import sys
import threading
import time
from flask import Flask, render_template, jsonify
import numpy as np

# Windows DLL yol kontrolü
if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(base_dir, "src")
    venv_scripts = os.path.join(base_dir, ".venv", "Scripts")
    if os.path.exists(src_dir):
        os.add_dll_directory(src_dir)
    if os.path.exists(venv_scripts):
        os.add_dll_directory(venv_scripts)

from rtlsdr import RtlSdr
from src.dsp import raw_bytes_to_iq, calculate_magnitude
from src.demodulator import find_preambles, demodulate_ppm
from src.decoder import extract_downlink_format, verify_crc, parse_df17
from src.cpr import decode_cpr_airborne
from src.routes import fetch_route

app = Flask(__name__)

aircraft_db = {}
callsign_route_cache = {}

CHUNK_SAMPLES = 262144
BYTES_PER_CHUNK = CHUNK_SAMPLES * 2


def process_packet(bits: list[int]):
    plane_info = parse_df17(bits)
    icao = plane_info["icao"]

    if icao not in aircraft_db:
        aircraft_db[icao] = {
            "icao": icao,
            "callsign": None,
            "route": None,
            "altitude_ft": None,
            "speed_kts": None,
            "heading_deg": None,
            "lat": None,
            "lon": None,
            "last_seen": time.time(),
            "even": None,
            "odd": None
        }

    entry = aircraft_db[icao]
    entry["last_seen"] = time.time()
    msg_type = plane_info.get("msg_type")

    # 1. Callsign güncellemesi (TC 1-4)
    if msg_type == "Aircraft Identification":
        raw_cs = plane_info.get("callsign")
        if raw_cs:
            callsign = raw_cs.strip()
            entry["callsign"] = callsign

            if callsign not in callsign_route_cache:
                route_result = fetch_route(callsign)
                callsign_route_cache[callsign] = route_result
                if route_result:
                    print(f"🛫 [ROTA] {callsign} ({icao}) : {route_result['origin']} ➔ {route_result['destination']}")

            entry["route"] = callsign_route_cache.get(callsign)

    # 2. İrtifa ve Konum güncellemesi (TC 9-18)
    elif msg_type == "Airborne Position":
        if plane_info.get("altitude_ft") is not None:
            entry["altitude_ft"] = plane_info["altitude_ft"]

        cpr_type = plane_info["cpr_type"].lower()
        entry[cpr_type] = plane_info

        if entry["even"] and entry["odd"]:
            coords = decode_cpr_airborne(entry["even"], entry["odd"])
            if coords:
                entry["lat"], entry["lon"] = coords

    # 3. Hız ve Rota Açısı (TC 19)
    elif msg_type == "Airborne Velocity":
        entry["speed_kts"] = plane_info.get("speed_kts")
        entry["heading_deg"] = plane_info.get("heading_deg")


def sdr_stream_worker():
    """Arka planda bağımsız çalışan RTL-SDR iş parçacığı"""
    print("[*] Harita motoru için RTL-SDR arka planda başlatılıyor...")
    sdr = RtlSdr()
    try:
        sdr.sample_rate = 2.0e6
        sdr.center_freq = 1090e6
        sdr.gain = 38.6
        time.sleep(0.15)
        print("[+] RTL-SDR dinleme devrede.")

        overlap_magnitude = None

        while True:
            raw_bytes = sdr.read_bytes(BYTES_PER_CHUNK)
            iq = raw_bytes_to_iq(raw_bytes)
            mag = calculate_magnitude(iq)

            if overlap_magnitude is not None:
                current_mag = np.concatenate((overlap_magnitude, mag))
            else:
                current_mag = mag

            overlap_magnitude = mag[-240:]
            preambles = find_preambles(current_mag, snr_threshold=3.0)

            for p_idx in preambles:
                bits = demodulate_ppm(current_mag, p_idx)
                if extract_downlink_format(bits) == 17 and verify_crc(bits):
                    process_packet(bits)

    except Exception as e:
        print(f"[-] SDR Akış Hatası: {e}")
    finally:
        sdr.close()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/data')
def get_data():
    """Tarayıcının polling yapıp son 60 saniyede canlı olan uçakları aldığı API"""
    now = time.time()
    active_planes = []

    # 60 saniyeden uzun süredir paket atmayan uçakları filtrele
    for plane in aircraft_db.values():
        if now - plane["last_seen"] < 60:
            active_planes.append({
                "icao": plane["icao"],
                "callsign": plane["callsign"],
                "route": plane["route"],
                "altitude_ft": plane["altitude_ft"],
                "speed_kts": plane["speed_kts"],
                "heading_deg": plane["heading_deg"],
                "lat": plane["lat"],
                "lon": plane["lon"]
            })

    return jsonify(active_planes)


if __name__ == '__main__':
    # SDR'ı arka planda bir thread olarak koştur
    thread = threading.Thread(target=sdr_stream_worker, daemon=True)
    thread.start()

    # Flask sunucusunu ayağa kaldır
    print("[+] Web Haritası Hazır: http://127.0.0.1:8080 adresini tarayıcında açabilirsin.\n")
    app.run(host='0.0.0.0', port=8080, debug=False)