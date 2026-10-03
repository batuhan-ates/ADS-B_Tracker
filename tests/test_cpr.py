import os
import sys

# Kök dizini yola ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.cpr import decode_cpr_airborne

# mode-s.org / ICAO Doc 9871 resmi referans paketleri
even_packet = {
    "cpr_lat": 93010,
    "cpr_lon": 51372,
}

odd_packet = {
    "cpr_lat": 74158,
    "cpr_lon": 50194,
    "last_received": "even",
}

print("🧪 [ICAO DOC 9871 CPR TESTİ ÇALIŞTIRILIYOR...]")
coords = decode_cpr_airborne(even_packet, odd_packet)

print(f"Hesaplanan Koordinat : {coords}")
print(f"Beklenen Koordinat   : (52.25766, 3.91937)")

# Test doğrulaması (Gerçek Even koordinatı 52.25766'dır)
assert coords is not None, "Koordinat çözülemedi!"
assert abs(coords[0] - 52.25766) < 0.0001, f"Enlem hesabı hatalı! Çıkan: {coords[0]}"
assert (
    abs(coords[1] - 3.91937) < 0.0001
), f"Boylam hesabı hatalı! Çıkan: {coords[1]}"

print("✅ CPR Birim Testi Başarıyla Tamamlandı!")