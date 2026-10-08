import os
import sys
import time
from numba import njit
import numpy as np

# Kök dizini yola ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.demodulator import find_preambles as find_preambles_pure_python
from src.dsp import calculate_magnitude, raw_bytes_to_iq

SAMPLE_FILE = "data/sample.bin"
SAMPLE_COUNT = 2_000_000  # 1 saniyelik veri (2.0 MSPS)


# =========================================================================
# 1. YÖNTEM: NumPy Vektörizasyonu (Dilimleme ve Maskeleme)
# =========================================================================
def find_preambles_numpy(
    magnitude: np.ndarray, snr_threshold: float = 3.0
) -> list[int]:
  noise_floor = np.mean(magnitude)
  min_peak_level = noise_floor * snr_threshold
  n = len(magnitude)

  if n < 240:
    return []

  # Kayan pencereyi dizinin kendisini ofsetleyerek SIMD/C seviyesine iteriz
  # 16 örneklik pencerenin tepe ve çukurlarını dilimlerle hizalayalım:
  # P0, P1, P2, P3 (0, 2, 7, 9. indeksler)
  p0 = magnitude[0 : n - 240]
  p1 = magnitude[2 : n - 238]
  p2 = magnitude[7 : n - 233]
  p3 = magnitude[9 : n - 231]

  high_energy = (p0 + p1 + p2 + p3) * 0.25

  # 12 adet çukur örneğinin toplamı
  low_sum = (
      magnitude[1 : n - 239]
      + magnitude[3 : n - 237]
      + magnitude[4 : n - 236]
      + magnitude[5 : n - 235]
      + magnitude[6 : n - 234]
      + magnitude[8 : n - 232]
      + magnitude[10 : n - 230]
      + magnitude[11 : n - 229]
      + magnitude[12 : n - 228]
      + magnitude[13 : n - 227]
      + magnitude[14 : n - 226]
      + magnitude[15 : n - 225]
  )
  low_energy = low_sum / 12.0

  # Vektörel mantıksal maske (Tüm 2 milyon eleman tek seferde C'de taranır)
  mask = (
      (p0 > min_peak_level)
      & (p0 > low_energy * 1.3)
      & (p1 > low_energy * 1.3)
      & (p2 > low_energy * 1.3)
      & (p3 > low_energy * 1.3)
      & (high_energy > low_energy * 1.8)
  )

  # True olan indeksleri al
  candidate_indices = np.flatnonzero(mask)

  # 240 örneklik çakışmaları (overlap) temizleme
  detected_indices = []
  last_idx = -240
  for idx in candidate_indices:
    if idx >= last_idx + 240:
      # Yerel zirve doğrulaması (Jitter önleme)
      if (
          idx > 0
          and magnitude[idx] >= magnitude[idx - 1]
          and magnitude[idx] >= magnitude[idx + 1]
      ):
        detected_indices.append(int(idx))
        last_idx = idx

  return detected_indices


# =========================================================================
# 2. YÖNTEM: Numba (@njit) ile C Seviyesine Derleme
# =========================================================================
@njit(fastmath=True)
def find_preambles_numba(magnitude: np.ndarray, snr_threshold: float = 3.0):
  noise_floor = np.mean(magnitude)
  min_peak_level = noise_floor * snr_threshold
  total_samples = len(magnitude)
  max_idx = total_samples - 240

  detected_indices = []
  i = 0

  while i < max_idx:
    if magnitude[i] < min_peak_level:
      i += 1
      continue

    p0 = magnitude[i]
    p1 = magnitude[i + 2]
    p2 = magnitude[i + 7]
    p3 = magnitude[i + 9]

    high_energy = (p0 + p1 + p2 + p3) * 0.25

    low_sum = (
        magnitude[i + 1]
        + magnitude[i + 3]
        + magnitude[i + 4]
        + magnitude[i + 5]
        + magnitude[i + 6]
        + magnitude[i + 8]
        + magnitude[i + 10]
        + magnitude[i + 11]
        + magnitude[i + 12]
        + magnitude[i + 13]
        + magnitude[i + 14]
        + magnitude[i + 15]
    )
    low_energy = low_sum / 12.0

    if (
        p0 > low_energy * 1.3
        and p1 > low_energy * 1.3
        and p2 > low_energy * 1.3
        and p3 > low_energy * 1.3
        and high_energy > (low_energy * 1.8)
        and high_energy > min_peak_level
    ):

      if (
          i > 0
          and magnitude[i] >= magnitude[i - 1]
          and magnitude[i] >= magnitude[i + 1]
      ):
        detected_indices.append(i)
        i += 240
        continue

    i += 1

  return detected_indices


# =========================================================================
# 3'LÜ KIYASLAMA TESTİ
# =========================================================================
def run_benchmark():
  if not os.path.exists(SAMPLE_FILE):
    print(f"[-] '{SAMPLE_FILE}' bulunamadı!")
    return

  print(f"[*] Veri yükleniyor ({SAMPLE_COUNT:,} örnek = 1 saniye)...")
  with open(SAMPLE_FILE, "rb") as f:
    raw_data = f.read(SAMPLE_COUNT * 2)

  iq = raw_bytes_to_iq(raw_data)
  magnitude = calculate_magnitude(iq)

  print(f"[+] Hazır! Test dizisi boyutu: {len(magnitude):,} örnek\n")
  print("=" * 70)

  # -------------------------------------------------------------
  # 1. Saf Python (BEFORE)
  # -------------------------------------------------------------
  print("⏱️  [1/3] Saf Python (Mevcut find_preambles) çalışıyor...")
  t0 = time.perf_counter()
  preambles_py = find_preambles_pure_python(magnitude, snr_threshold=3.0)
  t_py = time.perf_counter() - t0
  print(
      f"    ➜ Süre: {t_py:.4f} sn ({t_py * 1000:.1f} ms) | Bulunan:"
      f" {len(preambles_py)} paket"
  )

  # -------------------------------------------------------------
  # 2. NumPy Vektörizasyonu
  # -------------------------------------------------------------
  print("\n⏱️  [2/3] NumPy Vektörizasyonu çalışıyor...")
  t0 = time.perf_counter()
  preambles_np = find_preambles_numpy(magnitude, snr_threshold=3.0)
  t_np = time.perf_counter() - t0
  print(
      f"    ➜ Süre: {t_np:.4f} sn ({t_np * 1000:.1f} ms) | Bulunan:"
      f" {len(preambles_np)} paket"
  )

  # -------------------------------------------------------------
  # 3. Numba (@njit)
  # -------------------------------------------------------------
  print("\n⏱️  [3/3] Numba (@njit) JIT derleniyor ve çalışıyor...")
  # Isınma (JIT compilation süresini benchmark'a katmamak için)
  _ = find_preambles_numba(magnitude[:1000], 3.0)

  t0 = time.perf_counter()
  preambles_nb = find_preambles_numba(magnitude, snr_threshold=3.0)
  t_nb = time.perf_counter() - t0
  print(
      f"    ➜ Süre: {t_nb:.4f} sn ({t_nb * 1000:.1f} ms) | Bulunan:"
      f" {len(preambles_nb)} paket"
  )

  # -------------------------------------------------------------
  # ÖZET VE HIZLANMA TABLOSU
  # -------------------------------------------------------------
  print("\n" + "=" * 70)
  print(f"{'YÖNTEM':<22} | {'SÜRE (ms)':<12} | {'HIZLANMA':<12} | CANLI AKIŞ")
  print("-" * 70)
  print(
      f"{'Saf Python':<22} | {t_py * 1000:<12.1f} | {'1.0x (Referans)':<12} |"
      f" {'❌ Yetişemez' if t_py > 1.0 else '⚠️ Sınırda'}"
  )
  print(
      f"{'NumPy Vektörize':<22} | {t_np * 1000:<12.1f} |"
      f" {t_py / t_np:<10.1f}x  | {'✅ Yetişir' if t_np < 1.0 else '❌ Yetişemez'}"
  )
  print(
      f"{'Numba (@njit)':<22} | {t_nb * 1000:<12.1f} | {t_py / t_nb:<10.1f}x "
      f" | {'✅ Çok Rahat' if t_nb < 0.1 else '✅ Yetişir'}"
  )
  print("=" * 70)


if __name__ == "__main__":
  run_benchmark()