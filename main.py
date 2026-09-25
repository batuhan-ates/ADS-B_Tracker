import os
from src.dsp import raw_bytes_to_iq, calculate_magnitude

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

if __name__ == "__main__":
    main()