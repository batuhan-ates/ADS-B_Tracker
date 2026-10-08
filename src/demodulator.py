import numpy as np
from numba import njit

# =========================================================================
# NUMBA İLE DERLENEN ÇEKİRDEK DSP / DEMODÜLASYON İŞLEVLERİ
# =========================================================================

@njit(fastmath=True)
def find_preambles(magnitude: np.ndarray, snr_threshold: float = 3.0):
    """
    Genlik dizisi üzerinde 16 örneklik (8 µs) kayan pencereyi C hızında tarar.
    Tespit edilen paket başlangıç indekslerini bir int listesi olarak döndürür.
    """
    noise_floor = np.mean(magnitude)
    min_peak_level = noise_floor * snr_threshold
    total_samples = len(magnitude)
    max_idx = total_samples - 240

    detected_indices = []
    i = 0

    while i < max_idx:
        # Hızlı eleme: İlk örnek eşiğin altındaysa doğrudan sonraki örneğe kay
        if magnitude[i] < min_peak_level:
            i += 1
            continue

        # Preamble darbeleri: 0, 2, 7, 9. indeksler
        p0 = magnitude[i]
        p1 = magnitude[i + 2]
        p2 = magnitude[i + 7]
        p3 = magnitude[i + 9]

        high_energy = (p0 + p1 + p2 + p3) * 0.25

        # 12 çukur/boşluk örneğinin toplamı
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

        # Geometri Kriterleri:
        # 1. 4 tepenin her biri çukurların ortalamasından belirgin şekilde büyük olmalı
        # 2. Ortalama tepe gücü çukurların en az 1.8 katı olmalı
        # 3. Tepe gücü gürültü eşiğini aşmalı
        if (
            p0 > low_energy * 1.3
            and p1 > low_energy * 1.3
            and p2 > low_energy * 1.3
            and p3 > low_energy * 1.3
            and high_energy > (low_energy * 1.8)
            and high_energy > min_peak_level
        ):
            # Yerel zirve kontrolü (Darbe kaymasını önleme)
            if i > 0 and magnitude[i] >= magnitude[i - 1] and magnitude[i] >= magnitude[i + 1]:
                detected_indices.append(i)
                # ADS-B mesaj süresi (120 µs / 240 örnek) boyunca atla (çift tetiklemeyi önler)
                i += 240
                continue

        i += 1

    return detected_indices


@njit(fastmath=True)
def demodulate_ppm(magnitude: np.ndarray, preamble_start_idx: int):
    """
    Preamble bitişinden (16 örnek sonrası) itibaren 224 örneklik yükü
    112 adet mantıksal bite (1 ve 0) C hızında dönüştürür.
    """
    data_start = preamble_start_idx + 16
    bits = []

    for i in range(112):
        sample_a = magnitude[data_start + 2 * i]      # İlk yarı (0.0 - 0.5 µs)
        sample_b = magnitude[data_start + 2 * i + 1]  # İkinci yarı (0.5 - 1.0 µs)

        if sample_a > sample_b:
            bits.append(1)
        else:
            bits.append(0)

    return bits


# =========================================================================
# PROTOKOL / DÖNÜŞÜM İŞLEVLERİ (Python Standart)
# =========================================================================

def bits_to_hex(bits: list[int]) -> str:
    """
    112 bitlik listeyi standart 28 karakterlik Mode-S hex dizgisine çevirir.
    """
    bit_str = "".join(str(b) for b in bits)
    return "".join(f"{int(bit_str[i:i+4], 2):X}" for i in range(0, len(bit_str), 4))