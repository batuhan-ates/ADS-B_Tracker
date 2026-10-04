# tests/test_velocity.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.decoder import decode_velocity

def test_velocity_decoding():
    print("🧪 [ICAO DOC 9871 TC=19 VELOCITY TESTİ ÇALIŞTIRILIYOR...]")
    
    test_hex = "8D485020994409940838175B28C3"
    test_bits = [int(b) for b in bin(int(test_hex, 16))[2:].zfill(112)]
    
    res = decode_velocity(test_bits)
    print(f"    Yer Sürati  : {res['speed_kts']} kts ({res['speed_kmh']} km/h)")
    print(f"    Rota Açısı  : {res['heading_deg']}°")
    print(f"    Dikey Hız   : {res['vertical_rate_fpm']} ft/min")

    assert res["speed_kts"] == 159, f"Hız hatalı: {res['speed_kts']}"
    assert res["heading_deg"] == 182.9, f"Heading hatalı: {res['heading_deg']}"
    assert res["vertical_rate_fpm"] == -832, f"Dikey hız hatalı: {res['vertical_rate_fpm']}"

    print("✅ Velocity Birim Testi Kusursuz Geçti!")

if __name__ == "__main__":
    test_velocity_decoding()