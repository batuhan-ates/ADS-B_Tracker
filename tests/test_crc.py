import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Fonksiyonları dene:
from src.decoder import extract_downlink_format, verify_crc

# mode-s.org resmi altın referans paketi (Airborne Position)
REF_HEX = "8D4840D6202CC371C32CE0576098"

# Hex'i 112 bitlik listeye çevir:
bit_str = bin(int(REF_HEX, 16))[2:].zfill(112)
ref_bits = [int(b) for b in bit_str]

print(f"Karakter Sayısı : {len(REF_HEX)} (Beklenen: 28)")
print(f"Bit Uzunluğu    : {len(ref_bits)} (Beklenen: 112)")
print(f"Downlink Format : DF{extract_downlink_format(ref_bits)}")
print(f"CRC-24 Sonucu   : {verify_crc(ref_bits)}")