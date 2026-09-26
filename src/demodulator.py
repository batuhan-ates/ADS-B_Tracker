import numpy as np

# Preamble darbe (yüksek) ve çukur (alçak) indeksleri (2.0 MSPS standardı)
HIGH_INDICES = [0, 2, 7, 9]
LOW_INDICES = [1, 3, 4, 5, 6, 8, 10, 11, 12, 13, 14, 15]

def find_preambles(magnitude: np.ndarray, snr_threshold: float = 2.5) -> list[int]:
    """
    Genlik dizisi üzerinde 16 örneklik (8 µs) kayan pencere gezdirerek
    ADS-B Preamble başlangıç indekslerini tespit eder.
    
    :param magnitude: 1D mutlak genlik dizisi (|I + jQ|)
    :param snr_threshold: Darbelerin arka plan gürültüsünden kaç kat yüksek olması gerektiği
    :return: Tespit edilen preamble başlangıç örnek indekslerinin listesi
    """
    noise_floor = float(np.mean(magnitude))
    min_peak_level = noise_floor * snr_threshold
    
    detected_indices = []
    total_samples = len(magnitude)
    
    # 1 mesaj toplam 120 µs sürer (Preamble: 16 örnek + Payload: 224 örnek = 240 örnek)
    # Dizinin son 240 örneğine girmemek için sınırı ayarla
    i = 0
    max_idx = total_samples - 240
    
    while i < max_idx:
        # Hızlı eleme: İlk örnek eşiği geçemiyorsa doğrudan sonraki örneğe kay
        if magnitude[i] < min_peak_level:
            i += 1
            continue

        # 16 örneklik pencereyi al
        window = magnitude[i : i + 16]
        
        # 4 tepe noktasının ortalama genliği
        high_energy = np.mean(window[HIGH_INDICES])
        
        # 12 çukur/boşluk noktasının ortalama genliği
        low_energy = np.mean(window[LOW_INDICES])
        
        # Geometri Kriterleri:
        # 1. 4 tepenin her biri çukurların ortalamasından belirgin şekilde büyük olmalı
        # 2. Tepelerin ortalaması, çukurların en az 2 katı olmalı
        # 3. Tepelerin ortalaması gürültü eşiğini aşmalı
        is_peaks_valid = np.all(window[HIGH_INDICES] > low_energy * 1.3)
        is_ratio_valid = high_energy > (low_energy * 1.8)
        
        if is_peaks_valid and is_ratio_valid and (high_energy > min_peak_level):
            # Yerel tepe doğrulaması: Bir önceki veya bir sonraki örnek daha güçlü mü?
            # (Darbe kaymasını önleyip tam zirveye oturmak için)
            if magnitude[i] >= magnitude[i - 1] and magnitude[i] >= magnitude[i + 1]:
                detected_indices.append(i)
                # Bir ADS-B mesajı yakalandıysa, en az 120 µs (240 örnek) boyunca 
                # aynı uçağın başka bir paketi başlayamaz; pencereyi doğrudan 240 örnek ileri kaydır
                i += 240
                continue

        i += 1

    return detected_indices

def demodulate_ppm(magnitude: np.ndarray, preamble_start_idx: int) -> list[int]:
    """
    Preamble bitişinden (8 µs / 16 örnek sonrası) itibaren
    224 örneklik (112 µs) veriyi 112 adet bite (1 ve 0) dönüştürür.
    
    :param magnitude: 1D genlik dizisi
    :param preamble_start_idx: find_preambles ile bulunan başlangıç indeksi
    :return: 112 uzunluğunda [1, 0, ...] bit listesi
    """
    # Veri alanı Preamble'ın 16 örnek sonrasında başlar
    data_start = preamble_start_idx + 16
    
    # 112 bit * 2 örnek = 224 örnek
    payload_samples = magnitude[data_start : data_start + 224]
    
    bits = []
    for i in range(112):
        sample_a = payload_samples[2 * i]      # İlk yarı (0.0 - 0.5 µs)
        sample_b = payload_samples[2 * i + 1]  # İkinci yarı (0.5 - 1.0 µs)
        
        if sample_a > sample_b:
            bits.append(1)
        else:
            bits.append(0)
            
    return bits

def bits_to_hex(bits: list[int]) -> str:
    """
    112 bitlik listeyi standart 28 karakterlik Mode-S hex dizgisine çevirir.
    """
    bit_str = "".join(str(b) for b in bits)
    # Her 4 biti 1 hex karakterine çevir
    hex_str = "".join(f"{int(bit_str[i:i+4], 2):X}" for i in range(0, len(bit_str), 4))
    return hex_str