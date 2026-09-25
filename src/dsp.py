import numpy as np

def raw_bytes_to_iq(raw_bytes: bytes) -> np.ndarray:
    """
    RTL-SDR uint8 formatındaki ham bayt dizisini [-1.0, 1.0] aralığında 
    normalize edilmiş karmaşık (complex64) I/Q dizisine dönüştürür.
    
    RTL-SDR bayt dizilimi interleaved şekildedir: [I0, Q0, I1, Q1, I2, Q2, ...]
    """
    # 1. Ham baytları 32-bit float NumPy dizisine dök
    samples = np.frombuffer(raw_bytes, dtype=np.uint8).astype(np.float32)
    
    # 2. RTL-SDR'da 127.5 teorik DC orta noktasıdır (sıfır voltaj seviyesi).
    # 0..255 aralığını -1.0 ile +1.0 arasına normalize et.
    samples = (samples - 127.5) / 127.5
    
    # 3. Çift indeksler In-Phase (I), tek indeksler Quadrature (Q) bileşenleridir
    i_samples = samples[0::2]
    q_samples = samples[1::2]
    
    # 4. Karmaşık sayı (I + jQ) vektörünü oluştur
    iq = i_samples + 1j * q_samples
    return iq.astype(np.complex64)


def calculate_magnitude(iq_samples: np.ndarray) -> np.ndarray:
    """
    I/Q karmaşık sayılarının zarf/büyüklük (envelope/magnitude) değerini hesaplar.
    ADS-B (PPM) modülasyonunda veri bitleri genlik darbelerinde taşındığı için 
    faz bilgisi atılır ve sadece genlik incelenir.
    
    Formül: sqrt(I^2 + Q^2) -> np.abs(iq)
    """
    return np.abs(iq_samples).astype(np.float32)