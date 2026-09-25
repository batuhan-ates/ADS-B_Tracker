import os
import sys

# test.py dosyasının olduğu tam klasör yolu (src klasörü)
src_dir = os.path.dirname(os.path.abspath(__file__))

# Bir üst klasör yolu (ADS-B Tracker klasörü)
root_dir = os.path.dirname(src_dir)

# venv altındaki Scripts klasör yolu
venv_scripts = os.path.join(root_dir, ".venv", "Scripts")

# Windows'a tüm olası güncel DLL konumlarını zorla öğretiyoruz
if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
    os.add_dll_directory(src_dir)
    if os.path.exists(venv_scripts):
        os.add_dll_directory(venv_scripts)

try:
    from rtlsdr import RtlSdr
    sdr = RtlSdr()
    print("TEBRİKLER! Cihaz başarıyla bağlandı ve dither fonksiyonu tanındı.")
    sdr.close()
except Exception as e:
    print("HATA OLUŞTU:")
    print(e)