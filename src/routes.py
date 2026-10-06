# src/routes.py
import requests

def fetch_route(callsign: str) -> dict | None:
    """
    Callsign (örn: THY4AZ) için harici veritabanından 
    kalkış ve varış meydanlarını (ICAO kodları) sorgular.
    """
    clean_callsign = callsign.strip()
    url = f"https://opensky-network.org/api/routes?callsign={clean_callsign}"

    try:
        response = requests.get(url, timeout=2.0)
        if response.status_code == 200:
            data = response.json()
            route_info = data.get("route", [])
            if len(route_info) >= 2:
                return {
                    "origin": route_info[0],        # Örn: LTFM (İstanbul)
                    "destination": route_info[-1]    # Örn: EDDM (Münih)
                }
    except Exception:
        pass

    return None