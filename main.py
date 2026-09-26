import sys
import os
from src.dsp import raw_bytes_to_iq, calculate_magnitude
from src.demodulator import find_preambles, demodulate_ppm, bits_to_hex

SAMPLE_FILE = "data/sample.bin"

def main():
    if not os.path.exists(SAMPLE_FILE):
        print(f"[-] '{SAMPLE_FILE}' bulunamadı. Önce 'python src/capture.py' ile kayıt alın.")
        return

    print(f"[*] '{SAMPLE_FILE}' okunuyor...")
    with open(SAMPLE_FILE, "rb") as f:
        raw_data = f.read()

    # 1. Ham veriyi I/Q'ya çevir
    iq_samples = raw_bytes_to_iq(raw_data)
    print(f"[+] Toplam I/Q Örnek Sayısı : {len(iq_samples):,}")

    # 2. Genlik vektörünü çıkar
    magnitude = calculate_magnitude(iq_samples)
    print(f"[+] Ortalama Gürültü Tabanı : {magnitude.mean():.4f}")
    print(f"[+] En Yüksek Tepe Değeri   : {magnitude.max():.4f}")

    # 3. Preamble Tespiti
    preambles = find_preambles(magnitude, snr_threshold=3.0)
    print(f"[+] Toplam {len(preambles)} adet ADS-B mesajı yakalandı.\n")

# 4. PPM Bit Slicer ve Hex Çözümleme
    for idx, p_idx in enumerate(preambles, start=1):
        bits = demodulate_ppm(magnitude, p_idx)
        hex_msg = bits_to_hex(bits)
        
        # İlk 5 bit Downlink Format (DF) değerini verir
        df = int("".join(str(b) for b in bits[:5]), 2)
        
        print(f"--- Paket #{idx} (Örnek İndeksi: {p_idx:,}) ---")
        print(f"Downlink Format (DF) : DF{df}")
        print(f"112-Bit Hex Mesajı    : {hex_msg}")
        print(f"İlk 32 Bit (DF+CA+ICAO): {''.join(str(b) for b in bits[:32])}\n")

if __name__ == "__main__":
    main()