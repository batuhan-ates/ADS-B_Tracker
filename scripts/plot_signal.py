import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import matplotlib.pyplot as plt
from src.dsp import raw_bytes_to_iq, calculate_magnitude

SAMPLE_FILE = "data/sample.bin"
SAMPLE_RATE = 2.0e6  # 2.0 MSPS (1 örnek = 0.5 mikrosaniye)

def plot_peak_region(window_size: int = 1000):
    if not os.path.exists(SAMPLE_FILE):
        print(f"[-] '{SAMPLE_FILE}' bulunamadı. Önce capture.py ile kayıt yapın.")
        return

    print(f"[*] '{SAMPLE_FILE}' okunuyor...")
    with open(SAMPLE_FILE, "rb") as f:
        raw_data = f.read()

    # 1. Ham veriyi I/Q ve Genlik vektörüne dönüştür
    iq = raw_bytes_to_iq(raw_data)
    magnitude = calculate_magnitude(iq)

    # 2. En yüksek tepe noktasının (peak) indeksini bul
    peak_idx = int(np.argmax(magnitude))
    peak_val = magnitude[peak_idx]
    noise_floor = float(np.mean(magnitude))

    print(f"[+] En yüksek tepe indeksi : {peak_idx:,}")
    print(f"[+] Tepe genliği           : {peak_val:.4f}")
    print(f"[+] Ortalama gürültü       : {noise_floor:.4f}")

    # 3. Tepe noktasının etrafından bir pencere kes (Örn: 200 örnek öncesi, 800 örnek sonrası)
    start_idx = max(0, peak_idx - 200)
    end_idx = min(len(magnitude), start_idx + window_size)
    
    segment = magnitude[start_idx:end_idx]
    # Zaman eksenini mikrosaniye (us) cinsine çevir (2 MSPS -> her adım 0.5 us)
    time_us = np.arange(len(segment)) * (1.0 / SAMPLE_RATE) * 1e6

    # 4. Çizim
    plt.figure(figsize=(12, 5))
    plt.plot(time_us, segment, label="Sinyal Zarfı (Magnitude)", color="tab:blue", linewidth=1.2)
    plt.axhline(noise_floor, color="tab:red", linestyle="--", alpha=0.7, label=f"Gürültü Tabanı ({noise_floor:.4f})")
    plt.scatter([time_us[peak_idx - start_idx]], [peak_val], color="red", zorder=5, label=f"Maksimum Tepe ({peak_val:.4f})")

    plt.title(f"ADS-B Sinyal Darbesi (Tepe Bölgesi Analizi - Merkez İndeks: {peak_idx:,})", fontsize=12)
    plt.xlabel("Göreceli Zaman (µs - mikrosaniye)", fontsize=10)
    plt.ylabel("Normalize Genlik [0.0 - 1.0]", fontsize=10)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend(loc="upper right")
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    plot_peak_region(window_size=1000)