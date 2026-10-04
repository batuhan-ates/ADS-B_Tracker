# src/decoder.py
import math

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

def extract_icao(bits: list[int]) -> str:
    """112 bitlik ADS-B mesajından 24 bitlik ICAO adresini

    ayıklar ve 6 haneli Hexadecimal (büyük harf) metin olarak döner.
    Örnek: '4B2A66' veya '507CAB'
    """
    # 8. bitten 32. bite kadar olan 24 biti al
    icao_bits = bits[8:32]

    # 1 ve 0'ları yan yana getirip ikilik tabandaki metni oluştur
    icao_str = "".join(str(b) for b in icao_bits)

    # İkilik tabandan tamsayıya, oradan da 6 haneli büyük harfli Hex'e çevir
    icao_hex = f"{int(icao_str, 2):06X}"

    return icao_hex


def extract_type_code(bits: list[int]) -> int:
    """112 bitlik ADS-B mesajının ME alanından ilk 5 biti (Bit 32-36)

    okuyarak Type Code (TC / Tip Kodu) değerini tamsayı olarak döner.
    """
    # 32. bitten 37. bite kadar olan 5 biti al
    tc_bits = bits[32:37]

    # İkilik dizgiyi tamsayıya çevir
    tc_str = "".join(str(b) for b in tc_bits)
    type_code = int(tc_str, 2)

    return type_code

# --- ALT ÇÖZÜCÜLER (GÖVDE / PAYLOAD DECODERS) ---

# ICAO Doc 9871 standardı 6-bit karakter tablosu (64 eleman)
CALLSIGN_CHARS = (
    "#ABCDEFGHIJKLMNOPQRSTUVWXYZ##### "
    "###############0123456789######"
)

def decode_callsign(bits: list[int]) -> dict:
    """
    TC 1-4: 112 bitlik ADS-B mesajından uçağın 8 karakterlik 
    Çağrı Adını (Callsign / Flight Number) ayrıştırır.
    """
    # 40 ile 88. bitler arasındaki 48 biti al
    cs_bits = bits[40:88]
    callsign = []

    # 48 biti 6'şar bitlik 8 parçaya böl
    for i in range(8):
        chunk = cs_bits[i * 6 : (i + 1) * 6]
        val = int("".join(str(b) for b in chunk), 2)
        
        # Karakter tablosundan harfi/rakamı çek
        char = CALLSIGN_CHARS[val]
        callsign.append(char)

    # Sondaki dolgu boşluklarını ve geçersiz karakterleri temizle
    flight_id = "".join(callsign).replace("#", "").strip()

    return {
        "msg_type": "Aircraft Identification",
        "callsign": flight_id
    }

def decode_altitude(bits: list[int]) -> int | None:
  """40-51 bitleri arasındaki 12 bitlik barometrik irtifayı

  feet cinsine dönüştürür (ICAO Doc 9871).
  """
  # İrtifa alanı tüm pakette 40 ile 52. bitler arasıdır (12 bit)
  alt_bits = bits[40:52]

  # 47. bit (alt_bits'in 7. indeksi) Q-bitidir
  q_bit = alt_bits[7]

  if q_bit == 1:
    # Q-bitini (7. indeksi) çıkarıp kalan 11 biti birleştir
    n_bits = alt_bits[:7] + alt_bits[8:]
    n = int("".join(str(b) for b in n_bits), 2)

    # Standart ICAO Formülü
    altitude_ft = (n * 25) - 1000
    return altitude_ft
  else:
    # Gillham / Gray Code
    return None


def decode_airborne_position(bits: list[int]) -> dict:
  """TC 9-18: Havada Konum paketinden İrtifa ve CPR verilerini ayıklar."""
  altitude = decode_altitude(bits)

  # Bit 53: CPR Formatı (0: Even / Çift, 1: Odd / Tek)
  cpr_flag = bits[53]
  cpr_type = "Odd" if cpr_flag == 1 else "Even"

  # Bit 54-70: 17-bitlik CPR Enlem (Latitude)
  cpr_lat_str = "".join(str(b) for b in bits[54:71])
  cpr_lat = int(cpr_lat_str, 2)

  # Bit 71-87: 17-bitlik CPR Boylam (Longitude)
  cpr_lon_str = "".join(str(b) for b in bits[71:88])
  cpr_lon = int(cpr_lon_str, 2)

  return {
      "msg_type": "Airborne Position",
      "altitude_ft": altitude,
      "cpr_type": cpr_type,
      "cpr_lat": cpr_lat,
      "cpr_lon": cpr_lon,
      "cpr_lat_norm": cpr_lat / 131072.0,
      "cpr_lon_norm": cpr_lon / 131072.0,
  }

def decode_velocity(bits: list[int]) -> dict:
    """
    TC 19: Havada Hız (Airborne Velocity) telemetrisini ayrıştırır (ICAO Doc 9871).
    Yer sürati (knot), rota açısı (derece) ve dikey hızı (ft/dak) döner.
    """
    subtype = int("".join(str(b) for b in bits[37:40]), 2)
    
    # Subtype 1 & 2: Yer Sürati (Ground Speed)
    if subtype in (1, 2):
        # 1. Doğu-Batı Hız Bileşeni (V_ew) -> Bit 45: Yön, Bit 46-55: Değer
        ew_sign = bits[45]
        v_ew_raw = int("".join(str(b) for b in bits[46:56]), 2)
        v_ew = (v_ew_raw - 1) if v_ew_raw > 0 else 0
        v_x = -v_ew if ew_sign == 1 else v_ew

        # 2. Kuzey-Güney Hız Bileşeni (V_ns) -> Bit 56: Yön, Bit 57-66: Değer
        ns_sign = bits[56]
        v_ns_raw = int("".join(str(b) for b in bits[57:67]), 2)
        v_ns = (v_ns_raw - 1) if v_ns_raw > 0 else 0
        v_y = -v_ns if ns_sign == 1 else v_ns

        # 3. Bileşke Yer Sürati (Ground Speed)
        speed = round(math.sqrt(v_x**2 + v_y**2))

        # 4. Pusula Rota Açısı (Track / Heading)
        heading = 0.0
        if speed > 0:
            track = math.degrees(math.atan2(v_x, v_y))
            if track < 0:
                track += 360.0
            heading = round(track, 1)

        # 5. Dikey Hız (Vertical Rate) -> Bit 68: Yön, Bit 69-77: Değer
        vr_sign = bits[68]
        vr_raw = int("".join(str(b) for b in bits[69:78]), 2)
        vertical_rate = 0
        if vr_raw > 0:
            rate = (vr_raw - 1) * 64
            vertical_rate = -rate if vr_sign == 1 else rate

        return {
            "msg_type": "Airborne Velocity",
            "subtype": subtype,
            "speed_kts": speed,
            "speed_kmh": round(speed * 1.852),
            "heading_deg": heading,
            "vertical_rate_fpm": vertical_rate
        }

    return {
        "msg_type": "Airborne Velocity",
        "subtype": subtype,
        "note": "Airspeed formatı şimdilik desteklenmiyor."
    }
# --- ANA YÖNLENDİRİCİ FONKSİYON (ROUTER) ---


def parse_df17(bits: list[int]) -> dict:
    """DF17 mesajını alır; ICAO kimliğini ve Type Code'u (TC) ayıklar.

    TC değerine göre ilgili çözücü fonksiyona yönlendirir ve
    tüm bilgileri tek bir sözlükte (dict) birleştirip döner.
    """
    icao = extract_icao(bits)
    tc = extract_type_code(bits)

    # Temel uçak paketi bilgisi
    parsed_data = {"icao": icao, "type_code": tc, "msg_type": "Unknown / Other"}

    # TC değerine göre akıllı yönlendirme
    if 1 <= tc <= 4:
        payload_data = decode_callsign(bits)
        parsed_data.update(payload_data)

    elif 9 <= tc <= 18:
        payload_data = decode_airborne_position(bits)
        parsed_data.update(payload_data)

    elif tc == 19:
        payload_data = decode_velocity(bits)
        parsed_data.update(payload_data)

    return parsed_data

