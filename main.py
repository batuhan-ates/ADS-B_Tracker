import sys
import os
from src.dsp import raw_bytes_to_iq, calculate_magnitude
from src.demodulator import find_preambles, demodulate_ppm, bits_to_hex
from src.decoder import extract_downlink_format, verify_crc, extract_icao, extract_type_code, parse_df17

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

    valid_plane_count = 0
# 4. PPM Bit Slicer ve Hex Çözümleme
    for idx, p_idx in enumerate(preambles, start=1):
        bits = demodulate_ppm(magnitude, p_idx)
        hex_msg = bits_to_hex(bits)
        
        # Downlink Format (İlk 5 bit) kontrolü
        df = extract_downlink_format(bits)

        # DF 17 mi ve CRC tutuyor mu?
        if df == 17 and verify_crc(bits):

            valid_plane_count += 1
            plane_info = parse_df17(bits)
            hex_msg = bits_to_hex(bits)
            icao = extract_icao(bits)
            tc = extract_type_code(bits)
            
            print(f"✈️  [DOĞRULANMIŞ UÇAK] Örnek İndeksi: {p_idx:,}")
            print(f"    112-Bit Hex: {hex_msg}\n")
            print(f"    ICAO Adresi : {icao}")
            print(f"    Type Code   : {tc}")
            print(f"    Paket Türü  : {plane_info['msg_type']}\n")

            if plane_info.get("altitude_ft") is not None:
                alt = plane_info["altitude_ft"]
                alt_m = int(alt * 0.3048)
                print(f"    İrtifa      : {alt:,} ft ({alt_m:,} m)")
                print(f"    CPR Format  : {plane_info['cpr_type']}\n")
            else:
                print(f"    (Bu paket irtifa bilgisi taşımıyor)\n")

if __name__ == "__main__":
    main()