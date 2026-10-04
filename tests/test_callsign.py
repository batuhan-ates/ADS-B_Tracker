import sys
import os

# Kök dizini modül arama yoluna ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.decoder import decode_callsign

def test_callsign_decoding():
    print("🧪 [ICAO DOC 9871 CALLSIGN TESTİ ÇALIŞTIRILIYOR...]")
    
    # mode-s.org referans Callsign mesajı: KLM1023
    test_hex = "8D4840D6202CC371C32CE0576098"
    
    # Hex'i 112 bitlik listeye çevir
    test_bits = [int(b) for b in bin(int(test_hex, 16))[2:].zfill(112)]
    
    result = decode_callsign(test_bits)
    callsign = result.get("callsign")
    
    print(f"Çözülen Çağrı Adı : '{callsign}'")
    print(f"Beklenen          : 'KLM1023'")
    
    assert callsign == "KLM1023", f"Callsign çözümü hatalı! Çıkan: {callsign}"
    print("✅ Callsign Birim Testi Başarıyla Tamamlandı!")

if __name__ == "__main__":
    test_callsign_decoding()