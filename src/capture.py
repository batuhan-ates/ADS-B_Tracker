import os
import time
from rtlsdr import RtlSdr

def record_raw_samples(
    output_path: str = "data/sample_fm",
    duration_sec: float = 10.0,
    sample_rate: float = 2.0e6,
    center_freq: float = 98e6,
    gain: float = 38.6
):
    """
    RTL-SDR üzerinden 1090 MHz Mode-S/ADS-B ham I/Q verisini okur ve ikili (binary) olarak kaydeder.
    """
    # data/ klasörünün varlığından emin ol
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print(f"[*] RTL-SDR başlatılıyor...")
    sdr = RtlSdr()

    try:
        # Donanım ayarları
        sdr.sample_rate = sample_rate    # 2.0 MSPS (ADS-B darbe çözünürlüğü için standart)
        sdr.center_freq = center_freq    # 1090 MHz Taşıyıcı Frekans
        sdr.gain = gain                  # 'auto' veya dB cinsinden (örn: 49.6)

        # 2 MSPS hızında her I/Q örneği 2 bayttır (1 bayt I + 1 bayt Q)
        total_samples = int(duration_sec * sample_rate)
        bytes_to_read = total_samples * 2

        print(f"[*] Dinleme Frekansı: {center_freq / 1e6:.1f} MHz")
        print(f"[*] Süre            : {duration_sec} saniye")
        print(f"[*] Okunacak Boyut  : {bytes_to_read / (1024 * 1024):.2f} MB ({bytes_to_read:,} bayt)")
        
        # Tuner'ın frekansa oturması ve kazanç devresinin dengelenmesi için kısa bekleme
        time.sleep(0.1)

        print("[+] Kayıt başladı, anteni sabit tutun...")
        raw_bytes = sdr.read_bytes(bytes_to_read)

        with open(output_path, "wb") as f:
            f.write(raw_bytes)

        print(f"[✓] Kayıt tamamlandı -> '{output_path}'")

    finally:
        # Cihaz kilidini serbest bırak (USB portunun kilitlenmemesi için kritik)
        sdr.close()

if __name__ == "__main__":
    # 2 saniyelik test kaydı al (yaklaşık 8 MB veri üretir)
    record_raw_samples(output_path="data/sample_fm.bin", duration_sec=10.0)