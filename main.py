import sys
import os
from src.dsp import raw_bytes_to_iq, calculate_magnitude
from src.demodulator import find_preambles, demodulate_ppm, bits_to_hex
from src.decoder import extract_downlink_format, verify_crc, extract_icao, extract_type_code, parse_df17
from src.cpr import decode_cpr_airborne

SAMPLE_FILE = "data/sample.bin"

# Uçakların Even/Odd paketlerini tutacağımız dinamik hafıza
aircraft_db = {}

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
        df = extract_downlink_format(bits)

        # -------------------------------------------------------------
        # 1. KAPI: Sadece DF17 VE CRC hatasız olan gerçek uçaklar girer!
        # -------------------------------------------------------------
        if df == 17 and verify_crc(bits):
            plane_info = parse_df17(bits)

            # Geçici TC=12 Filtresi (1. Kapının içinde!)
            if plane_info["type_code"] == 12:
                valid_plane_count += 1
                hex_msg = bits_to_hex(bits)

                print(f"✈️  [TC=12 KONUM PAKETİ #{valid_plane_count}] Örnek İndeksi: {p_idx:,}")
                print(f"    112-Bit Hex : {hex_msg}")
                print(f"    ICAO Adresi : {plane_info['icao']}")
                print(f"    Type Code   : {plane_info['type_code']}")
                print(f"    Paket Türü  : {plane_info['msg_type']}")
                print(f"    İrtifa      : {plane_info.get('altitude_ft')} ft")
                print(f"    CPR Format  : {plane_info.get('cpr_type')}")
                print(f"    Ham CPR Lat : {plane_info.get('cpr_lat')}")
                print(f"    Ham CPR Lon : {plane_info.get('cpr_lon')}")

                # CPR Durum Takibi (1. Kapının içinde!)
                icao = plane_info["icao"]
                cpr_type = plane_info["cpr_type"].lower()

                if icao not in aircraft_db:
                    aircraft_db[icao] = {}

                aircraft_db[icao][cpr_type] = plane_info

                # İki kare birikti mi kontrolü
                if "even" in aircraft_db[icao] and "odd" in aircraft_db[icao]:
                    even_pkt = aircraft_db[icao]["even"]
                    odd_pkt = aircraft_db[icao]["odd"]
                    odd_pkt["last_received"] = cpr_type

                    coords = decode_cpr_airborne(even_pkt, odd_pkt)
                    if coords:
                        lat, lon = coords
                        print(f"    📍 [KOORDİNAT]")
                        print(f"       Enlem (Lat) : {lat:.5f}°")
                        print(f"       Boylam (Lon): {lon:.5f}°")
                        print(f"       Harita Linki: https://www.google.com/maps?q={lat:.5f},{lon:.5f}")
                else:
                    print(f"    ⏳ [BEKLİYOR] Şimdilik sadece '{cpr_type.upper()}' karesi geldi. Zıt kare bekleniyor...")

                print()

if __name__ == "__main__":
    main()