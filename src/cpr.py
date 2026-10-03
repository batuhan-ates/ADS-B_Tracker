import math


def cpr_nl(lat: float) -> int:
    """Enlem değerine göre o paraleldeki boylam bölge sayısını (NL) hesaplar.

    Kutuplara yaklaştıkça boylam aralıkları daraldığı için dilim sayısı azalır.
    """
    if abs(lat) >= 87.0:
        return 1
    if abs(lat) == 0.0:
        return 59

    # ICAO Doc 9871 NL Formülü
    num = 1 - math.cos(math.pi / 30.0)
    den = math.cos(math.radians(lat)) ** 2

    # Truncation/domain hatasını önlemek için sınır kontrolü
    val = 1.0 - (num / den)
    if val < -1.0:
        return 1

    nl = math.floor(2.0 * math.pi / math.acos(val))
    return int(nl)


def decode_cpr_airborne(
    even_packet: dict, odd_packet: dict
) -> tuple[float, float] | None:
    """Even ve Odd paketlerini birlikte işleyerek uçağın küresel

    enlem ve boylam (Latitude, Longitude) koordinatlarını çözer.

    :param even_packet: decode_airborne_position'dan dönen Even sözlüğü
    :param odd_packet: decode_airborne_position'dan dönen Odd sözlüğü
    :return: (enlem, boylam) demeti (float, float) veya None
    """
    # 1. 17-bitlik CPR değerlerini [0, 1) arasına normalize et
    yz_even = even_packet["cpr_lat"] / 131072.0
    yz_odd = odd_packet["cpr_lat"] / 131072.0

    xz_even = even_packet["cpr_lon"] / 131072.0
    xz_odd = odd_packet["cpr_lon"] / 131072.0

    # 2. Enlem Dilim İndeksi (j) Hesabı
    j = math.floor(59.0 * yz_even - 60.0 * yz_odd + 0.5)

    # Dilim genişlikleri
    d_lat_even = 360.0 / 60.0
    d_lat_odd = 360.0 / 59.0

    # 3. İki karenin enlemlerini hesapla
    lat_even = d_lat_even * ((j % 60) + yz_even)
    lat_odd = d_lat_odd * ((j % 59) + yz_odd)

    # Güney yarımküre dönüşümü (-90 ile +90 aralığı)
    if lat_even >= 270.0:
        lat_even -= 360.0
    if lat_odd >= 270.0:
        lat_odd -= 360.0

    # En güncel gelen pakete göre nihai enlem ve NL seçimi
    # (Son gelen Odd ise Odd baz alınır, Even ise Even)
    last_type = odd_packet.get("last_received", "even").lower()
    
    if last_type == "even":
      lat = lat_even
      nl = cpr_nl(lat)
      if nl > 0:
        m = math.floor(xz_even * (nl - 1) - xz_odd * nl + 0.5)
        d_lon = 360.0 / nl
        lon = d_lon * ((m % nl) + xz_even)
      else:
        lon = xz_even
    else:
      lat = lat_odd
      nl = cpr_nl(lat)
      n_odd = max(nl - 1, 1)
      m = math.floor(xz_even * (nl - 1) - xz_odd * nl + 0.5)
      d_lon = 360.0 / n_odd
      lon = d_lon * ((m % n_odd) + xz_odd)

    # Batı boylamı dönüşümü (-180 ile +180 aralığı)
    if lon >= 180.0:
        lon -= 360.0

    return round(lat, 5), round(lon, 5)