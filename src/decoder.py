# src/decoder.py

GENERATOR_POLY = 0xFFFA0480


def extract_downlink_format(bits: list[int]) -> int:
    """112 bitlik mesajın ilk 5 bitini okuyarak

    Downlink Format (DF) değerini tamsayı olarak döndürür.
    """
    df_bits = bits[:5]
    df_str = "".join(str(b) for b in df_bits)
    return int(df_str, 2)


def modes_checksum(msg_bits: list[int]) -> int:
    """
    İlk 88 bit üzerinden 24-bit CRC kalıntısını hesaplar.
    """
    crc = 0
    # İlk 88 bit veri + 24 adet 0 biti (toplam 112 adım)
    bits_to_process = msg_bits[:88] + [0] * 24
    
    for bit in bits_to_process:
        # En soldaki (MSB) bit dışarı taşıyor mu?
        msb = (crc >> 23) & 1
        
        # Register'ı 1 bit sola kaydır ve yeni gelen biti en sağa ekle
        crc = ((crc << 1) | bit) & 0xFFFFFF
        
        # Eğer en tepe bit 1 ise polinom ile XOR'la
        if msb:
            crc ^= 0x1FFF409  # Generator polinomunun alt 24 biti
            
    return crc

def verify_crc(bits: list[int]) -> bool:
    """
    Paketin son 24 bitindeki Parity ile hesaplanan CRC'yi karşılaştırır.
    """
    if len(bits) < 112:
        return False
        
    calculated_crc = modes_checksum(bits)
    
    # Paketin içindeki son 24 bit
    actual_parity = 0
    for b in bits[88:112]:
        actual_parity = (actual_parity << 1) | b
        
    return calculated_crc == actual_parity