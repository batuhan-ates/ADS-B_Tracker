import sys
import os
import numpy as np
import matplotlib.pyplot as plt
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.dsp import raw_bytes_to_iq, calculate_magnitude
from src.demodulator import find_preambles


SAMPLE_FILE = "data/sample.bin"
SAMPLE_RATE = 2.0e6

def plot_detected_preambles():
    if not os.path.exists(SAMPLE_FILE):
        print(f"[-] '{SAMPLE_FILE}' bulunamadı!")
        return

    print(f"[*] Veri okunuyor: {SAMPLE_FILE}...")
    with open(SAMPLE_FILE, "rb") as f:
        raw_data = f.read()

    iq = raw_bytes_to_iq(raw_data)
    magnitude = calculate_magnitude(iq)

    print(f"[*] Preamble araması başlatılıyor...")
    preambles = find_preambles(magnitude, snr_threshold=3.0)
    print(f"[+] Toplam {len(preambles)} adet ADS-B Preamble adayı yakalandı!")

    if not preambles:
        print("[-] Uygun preamble bulunamadı. Eşik değerini kontrol edin.")
        return

    # İlk yakalanan preamble'a odaklan
    target_idx = preambles[0]
    print(f"[+] İnceleme indeksi: {target_idx:,} (Zaman: {target_idx / SAMPLE_RATE:.4f} sn)")

    # Preamble (16 örnek) + Mesaj Başlangıcı (32 örnek) toplam 48 örneklik bir pencere çiz
    window_samples = 48
    segment = magnitude[target_idx : target_idx + window_samples]
    time_us = np.arange(len(segment)) * 0.5  # 2 MSPS'te her örnek 0.5 µs

    plt.figure(figsize=(12, 5))
    plt.plot(time_us, segment, marker="o", color="tab:blue", label="Sinyal Genliği")

    # 4 Darbeyi Kırmızıyla İşaretle (0, 1.0, 3.5, 4.5 µs)
    peak_times = [0.0, 1.0, 3.5, 4.5]
    peak_vals = [magnitude[target_idx + 0], magnitude[target_idx + 2], 
                 magnitude[target_idx + 7], magnitude[target_idx + 9]]
    plt.scatter(peak_times, peak_vals, color="red", s=80, zorder=5, label="Preamble Darbeleri (P1-P4)")

    # 8 µs sınır çizgisi (Preamble bitişi, Veri başlangıcı)
    plt.axvline(8.0, color="green", linestyle="--", linewidth=1.5, label="Veri Başlangıcı (8.0 µs)")

    plt.title(f"ADS-B Preamble Tespiti (Örnek İndeksi: {target_idx:,})", fontsize=12)
    plt.xlabel("Süre (µs)", fontsize=10)
    plt.ylabel("Genlik", fontsize=10)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend()
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    plot_detected_preambles()