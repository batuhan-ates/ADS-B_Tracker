import os
import sys
import time
import numpy as np
from rtlsdr import RtlSdr

# Kök dizini yola ekle (src modüllerine erişebilmek için)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.dsp import raw_bytes_to_iq, calculate_magnitude
from src.demodulator import find_preambles, demodulate_ppm
from src.decoder import extract_downlink_format, verify_crc

# --- Donanım ve Test Yapılandırması ---
CENTER_FREQ = 1090e6          # 1090 MHz ADS-B
SAMPLE_RATE = 2.0e6           # 2.0 MSPS
TEST_DURATION = 3.0           # Her kazanç adımında dinleme süresi (sn)

# RTL-SDR USB aktarımı 512 baytın katı olmak zorundadır (Short read hatasını engeller)
raw_target = int(SAMPLE_RATE * TEST_DURATION * 2)
TOTAL_BYTES = (raw_target // 512) * 512

# Taranacak R820T/R820T2 kazanç basamakları (dB)
CANDIDATE_GAINS = [15.7, 22.9, 28.0, 33.8, 38.6, 42.1, 44.5, 49.6]


def safe_read_bytes(sdr, num_bytes):
    """USB tamponundaki hizalama farklarına karşı güvenli okuma yapar."""
    try:
        return sdr.read_bytes(num_bytes)
    except OSError:
        # Donanım son bloğu eksik tamamlarsa bir önceki 512 baytlık sınırdan oku
        return sdr.read_bytes(num_bytes - 512)


def run_gain_sweep():
    print("=" * 80)
    print("       RTL-SDR KAZANÇ TARAMASI (GAIN SWEEP) - 1090 MHz ADS-B")
    print(f"       Her kademe için süre: {TEST_DURATION:.1f} sn | Okunacak: {TOTAL_BYTES:,} bayt")
    print("=" * 80)

    sdr = RtlSdr()
    results = []

    try:
        sdr.sample_rate = SAMPLE_RATE
        sdr.center_freq = CENTER_FREQ

        for gain in CANDIDATE_GAINS:
            sdr.gain = gain
            time.sleep(0.15)  # Tuner'ın kazanç devresinin oturması için bekleme

            print(f"\n[*] Kazanç: {gain:4.1f} dB | Dinleniyor...", end="", flush=True)

            # 1. 512 bayta hizalı güvenli ham okuma
            raw_bytes = safe_read_bytes(sdr, TOTAL_BYTES)
            raw_arr = np.frombuffer(raw_bytes, dtype=np.uint8)

            # 2. Clipping Oranı (0 ve 255'e vuran ADC limitleri)
            clipped_count = np.sum((raw_arr == 0) | (raw_arr == 255))
            clip_ratio = (clipped_count / len(raw_arr)) * 100.0

            # 3. DSP: I/Q Ayrıştırma ve Genlik
            iq = raw_bytes_to_iq(raw_bytes)
            mag = calculate_magnitude(iq)

            noise_floor = float(np.mean(mag))
            peak_val = float(np.max(mag))

            # 4. Preamble Tespiti ve DF17 / CRC-24 Doğrulaması
            preambles = find_preambles(mag, snr_threshold=3.0)
            valid_df17_count = 0

            for p_idx in preambles:
                bits = demodulate_ppm(mag, p_idx)
                df = extract_downlink_format(bits)
                if df == 17 and verify_crc(bits):
                    valid_df17_count += 1

            print(f" Bitti! (Geçerli Uçak Paketi: {valid_df17_count})")

            results.append({
                "gain": gain,
                "noise": noise_floor,
                "peak": peak_val,
                "clipping": clip_ratio,
                "preambles": len(preambles),
                "valid_df17": valid_df17_count
            })

    except KeyboardInterrupt:
        print("\n[!] Test kullanıcı tarafından durduruldu.")
    finally:
        sdr.close()
        print("\n[✓] RTL-SDR bağlantısı güvenle kapatıldı.")

    # =========================================================================
    # ANALİZ VE SONUÇ TABLOSU
    # =========================================================================
    if not results:
        return

    print("\n" + "=" * 80)
    print(f"{'KAZANÇ (dB)':<12} | {'TABAN GÜRÜLTÜ':<14} | {'CLIPPING (%)':<14} | {'ADAY TETİK':<12} | {'GEÇERLİ DF17'}")
    print("-" * 80)

    best_gain = None
    max_df17 = -1

    for r in results:
        print(f"{r['gain']:<12.1f} | {r['noise']:<14.4f} | %{r['clipping']:<13.3f} | {r['preambles']:<12} | {r['valid_df17']}")
        if r['valid_df17'] > max_df17:
            max_df17 = r['valid_df17']
            best_gain = r['gain']

    print("=" * 80)

    if max_df17 > 0:
        print(f"🎯 EN İYİ ÇALIŞMA KAZANCI: {best_gain} dB ({max_df17} adet hatasız CRC uçak paketi)")
    else:
        print("ℹ️  3 saniyede hava boşluğuna denk gelmiş olabilirsin. 'TEST_DURATION = 5.0' yapıp tekrar deneyebilirsin.")


if __name__ == "__main__":
    run_gain_sweep()