# flight_tool.py
#
# This module parses natural-language flight queries, resolves locations to
# IATA airport codes, and fetches live flight status data from the AviationStack
# API. It also formats flight results for display and handles common query
# patterns like "from X to Y", "flights to X", and country/city mentions.

# Standard library imports:
import os  # access environment variables and set request cert paths
import re  # regular expressions for parsing user queries and cleaning text

# Third-party imports:
import certifi  # provides a trusted SSL/TLS certificate bundle for requests
import airportsdata  # loads airport metadata keyed by IATA code
import pycountry  # resolves country names and ISO country codes
import requests  # performs HTTP requests to the AviationStack API
from dotenv import load_dotenv  # loads environment variables from a .env file

# Load environment variables from a .env file, if present.
load_dotenv()

# Use certifi's certificate bundle for SSL requests.
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

# API key for AviationStack, loaded from environment variables.
API_KEY = os.getenv("AVIATIONSTACK_API_KEY")

# Default departure airport code used when only a destination is provided.
DEFAULT_ORIGIN_IATA = os.getenv("DEFAULT_ORIGIN_IATA", "JFK")

# AviationStack endpoint for live flight data.
BASE_URL = "http://api.aviationstack.com/v1/flights"

# Load a dictionary of airports keyed by IATA code.
AIRPORTS = airportsdata.load("IATA")

COUNTRY_ALIASES = {
    "USA": "US",
    "UK": "GB",
    "UAE": "AE",
    "South Korea": "KR",
    "North Korea": "KP",
    "Russia": "RU",
    "Vietnam": "VN",
    "Iran": "IR",
    "Syria": "SY",
    "Venezuela": "VE",
    "Bolivia": "BO",
    "Moldova": "MD",
    "Tanzania": "TZ",
    "Laos": "LA",
    "Brunei": "BN",
    "Czech Republic": "CZ",
    "Slovakia": "SK",
    "Ivory Coast": "CI",
    "Republic of the Congo": "CG",
    "Democratic Republic of the Congo": "CD",
    "Eswatini": "SZ",
    "Burma": "MM",
    "India": "IN",
    "China": "CN",
    "Taiwan": "TW",
    "Hong Kong": "HK",
    "Macau": "MO",
    "United Kingdom": "GB",
    "Germany": "DE",
    "France": "FR",
    "Italy": "IT",
    "Spain": "ES",
    "Portugal": "PT",
    "Netherlands": "NL",
    "Belgium": "BE",
    "Switzerland": "CH",
    "Austria": "AT",
    "Sweden": "SE",
    "Norway": "NO",
    "Finland": "FI",
    "Denmark": "DK",
    "Poland": "PL",
    "Czechia": "CZ",
    "Slovakia": "SK",
    "Hungary": "HU",
    "Greece": "GR",
    "Turkey": "TR",
    "Israel": "IL",
    "Saudi Arabia": "SA",
    "United Arab Emirates": "AE",
    "Qatar": "QA",
    "Kuwait": "KW",
    "Bahrain": "BH"
}

COUNTRY_MAIN_AIRPORT = {
    "IN": "DEL",  # India - Delhi
    "CN": "PEK",  # China - Beijing
    "JP": "NRT",  # Japan - Narita
    "KR": "ICN",  # South Korea - Incheon
    "TW": "TPE",  # Taiwan - Taipei
    "HK": "HKG",  # Hong Kong - Hong Kong
    "MO": "MFM",  # Macau - Macau
    "GB": "LHR",  # United Kingdom - London Heathrow
    "DE": "FRA",  # Germany - Frankfurt
    "FR": "CDG",  # France - Paris Charles de Gaulle
    "IT": "FCO",  # Italy - Rome Fiumicino
    "ES": "MAD",  # Spain - Madrid Barajas
    "PT": "LIS",  # Portugal - Lisbon
    "NL": "AMS",  # Netherlands - Amsterdam Schiphol
    "BE": "BRU",  # Belgium - Brussels National
    "CH": "ZRH",  # Switzerland - Zurich
    "AT": "VIE",  # Austria - Vienna
    "SE": "ARN",  # Sweden - Stockholm Arlanda
    "NO": "OSL",  # Norway - Oslo Gardermoen
    "FI": "HEL",  # Finland - Helsinki Vantaa
    "DK": "CPH",  # Denmark - Copenhagen Kastrup
    "PL": "WAW",  # Poland - Warsaw Chopin
    "CZ": "PRG",  # Czech Republic - Prague Ruzyne
    "SK": "BTS",  # Slovakia - Bratislava M. R. Štefánik
    "HU": "BUD",  # Hungary - Budapest Ferenc Liszt
    "GR": "ATH",  # Greece - Athens Eleftherios Venizelos
    "TR": "IST",  # Turkey - Istanbul Airport
    "IL": "TLV",  # Israel - Tel Aviv Ben Gurion
    "SA": "RUH",  # Saudi Arabia - Riyadh King Khalid
    "AE": "DXB",  # United Arab Emirates - Dubai International
    "QA": "DOH",  # Qatar - Doha Hamad
}

CITY_MAIN_AIRPORT = {
    "delhi": "DEL",
    "new delhi": "DEL",
    "mumbai": "BOM",
    "kolkata": "CCU",
    "chennai": "MAA",
    "bangalore": "BLR",
    "bengaluru": "BLR",
    "tokyo": "NRT",
    "osaka": "KIX",
    "kyoto": "KIX",
    "new york": "JFK",
    "london": "LHR",
    "dubai": "DXB",
    "singapore": "SIN",
    "kuala lumpur": "KUL",
    "bangkok": "BKK",
    "doha": "DOH",
    "istanbul": "IST",
    "toronto": "YYZ",
    "sydney": "SYD",
    "paris": "CDG",
    "rome": "FCO",
    "madrid": "MAD",
    "frankfurt": "FRA",
}


def clean_text(text: str) -> str:
    """Normalize text for location matching.

    This removes punctuation, collapses whitespace, and strips common travel
    keywords that are not useful for identifying places.
    """
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    stop_words = [
        "flight", "flights", "ticket", "tickets", "trip", "travel",
        "plan", "complete", "days", "day", "including", "hotel",
        "hotels", "sightseeing", "under", "budget", "info", "information"
    ]
    words = [w for w in text.split() if w not in stop_words]
    return " ".join(words).strip()



def country_name_to_code(text: str):
    """Convert a country or alias text into an ISO alpha-2 country code."""
    text = clean_text(text)

    if text in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[text]

    try:
        country = pycountry.countries.lookup(text)
        return country.alpha_2
    except LookupError:
        pass

    # Detect country name inside longer text
    for country in pycountry.countries:
        country_name = country.name.lower()
        if country_name in text:
            return country.alpha_2

    for alias, code in COUNTRY_ALIASES.items():
        if alias in text:
            return code

    return None



def airport_country_matches(airport: dict, country_code: str) -> bool:
    """Check whether an airport object belongs to a specific country code."""
    airport_country = str(airport.get("country", "")).upper().strip()

    if airport_country == country_code:
        return True

    try:
        country = pycountry.countries.get(alpha_2=country_code)
        if country and airport_country.lower() == country.name.lower():
            return True
    except Exception:
        pass

    return False




def get_best_airport_for_country(country_code: str):
    """Return the best airport for a country.

    Uses a preferred airport if available, otherwise scores candidates based on
    airport name and city attributes.
    """
    preferred = COUNTRY_MAIN_AIRPORT.get(country_code)

    if preferred and preferred in AIRPORTS:
        return preferred

    candidates = []

    for iata, airport in AIRPORTS.items():
        if not iata:
            continue

        if airport_country_matches(airport, country_code):
            name = str(airport.get("name", "")).lower()
            city = str(airport.get("city", "")).lower()

            score = 0

            if "international" in name:
                score += 50
            if "intl" in name:
                score += 40
            if "capital" in name:
                score += 20
            if city:
                score += 5

            candidates.append((score, iata))

    if not candidates:
        return None

    candidates.sort(reverse=True)
    return candidates[0][1]




def resolve_location_to_iata(location: str):
    """
    Convert a freeform location to an airport IATA code.

    This supports direct IATA codes, city names, country names, and other
    airport database matches.
    """

    if not location:
        return None

    raw_location = location.strip()

    # Direct IATA code
    if re.fullmatch(r"[A-Za-z]{3}", raw_location):
        code = raw_location.upper()
        if code in AIRPORTS:
            return code

    location_clean = clean_text(raw_location)

    if not location_clean:
        return None

    # City preferred airport
    if location_clean in CITY_MAIN_AIRPORT:
        return CITY_MAIN_AIRPORT[location_clean]

    # Country preferred airport
    country_code = country_name_to_code(location_clean)
    if country_code:
        airport = get_best_airport_for_country(country_code)
        if airport:
            return airport

    # Exact city match from airport database as a last fallback.
    city_matches = []

    for iata, airport in AIRPORTS.items():
        city = str(airport.get("city", "")).lower().strip()
        name = str(airport.get("name", "")).lower().strip()

        score = 0

        if city == location_clean:
            score += 100
        elif location_clean in city:
            score += 70

        if location_clean in name:
            score += 50

        if "international" in name:
            score += 10

        if score > 0:
            city_matches.append((score, iata))

    if city_matches:
        city_matches.sort(reverse=True)
        return city_matches[0][1]

    return None




def find_location_mentions(query: str):
    """Extract likely country or city mentions from a query string."""

    q = query.lower()
    mentions = []

    # Country aliases
    for alias in COUNTRY_ALIASES:
        if re.search(rf"\b{re.escape(alias)}\b", q):
            mentions.append(alias)

    # Country names from pycountry
    for country in pycountry.countries:
        name = country.name.lower()
        if len(name) >= 4 and re.search(rf"\b{re.escape(name)}\b", q):
            mentions.append(name)

    # City names from our preferred city map
    for city in CITY_MAIN_AIRPORT:
        if re.search(rf"\b{re.escape(city)}\b", q):
            mentions.append(city)

    # Remove duplicate mentions while preserving the original order.
    unique_mentions = []
    for item in mentions:
        if item not in unique_mentions:
            unique_mentions.append(item)

    return unique_mentions


def parse_route(query: str):
    """Extract departure and arrival IATA codes from a natural-language query."""

    # Return values: (dep_iata, arr_iata)
    # None, None --> global live flights
    # DAC, NRT   --> flight route filter
    # DAC, None  --> flights departing from DAC
    # None, NRT  --> flights arriving to NRT

    q = query.strip()
    q_lower = q.lower()

    # If the query asks for global or worldwide flights, do not filter by route.
    global_keywords = [
        "all country",
        "all countries",
        "global flight",
        "global flights",
        "all flight",
        "all flights",
        "worldwide flight",
        "worldwide flights",
    ]

    if any(keyword in q_lower for keyword in global_keywords):
        return None, None

    # If the user provides two IATA codes, treat these as departure and arrival.
    codes = re.findall(r"\b[A-Z]{3}\b", q)

    if len(codes) >= 2:
        dep = codes[0].upper()
        arr = codes[1].upper()
        return dep, arr

    # Pattern: from X to Y
    match = re.search(
        r"\bfrom\s+(.+?)\s+\bto\s+(.+?)(?:\s+(?:on|for|under|including|with|in|at)\b|[.!?]|$)",
        q_lower,
    )

    if match:
        origin_text = match.group(1)
        dest_text = match.group(2)

        dep_iata = resolve_location_to_iata(origin_text)
        arr_iata = resolve_location_to_iata(dest_text)

        return dep_iata, arr_iata

    # Pattern: to Y from X
    match = re.search(
        r"\bto\s+(.+?)\s+\bfrom\s+(.+?)(?:\s+(?:on|for|under|including|with|in|at)\b|[.!?]|$)",
        q_lower,
    )

    if match:
        dest_text = match.group(1)
        origin_text = match.group(2)

        dep_iata = resolve_location_to_iata(origin_text)
        arr_iata = resolve_location_to_iata(dest_text)

        return dep_iata, arr_iata

    # Pattern: flights from X
    match = re.search(r"\bfrom\s+(.+?)(?:[.!?]|$)", q_lower)

    if match:
        origin_text = match.group(1)
        dep_iata = resolve_location_to_iata(origin_text)
        return dep_iata, None

    # Pattern: flights to X
    match = re.search(r"\bto\s+(.+?)(?:[.!?]|$)", q_lower)

    if match:
        dest_text = match.group(1)
        arr_iata = resolve_location_to_iata(dest_text)
        return None, arr_iata

    # Fallback: if no explicit route is found, extract mentions from the query.
    mentions = find_location_mentions(q)

    if len(mentions) >= 2:
        dep_iata = resolve_location_to_iata(mentions[0])
        arr_iata = resolve_location_to_iata(mentions[1])
        return dep_iata, arr_iata

    if len(mentions) == 1:
        arr_iata = resolve_location_to_iata(mentions[0])
        return DEFAULT_ORIGIN_IATA, arr_iata

    return None, None


def format_flight(flight: dict):
    """Format a single flight record into a readable multiline summary."""
    airline = flight.get("airline", {}).get("name") or "Unknown airline"
    flight_number = flight.get("flight", {}).get("iata") or "Unknown flight number"
    status = flight.get("flight_status") or "Unknown"

    dep = flight.get("departure", {}) or {}
    arr = flight.get("arrival", {}) or {}

    dep_airport = dep.get("airport") or "Unknown departure airport"
    dep_iata = dep.get("iata") or "Unknown"
    dep_terminal = dep.get("terminal") or "N/A"
    dep_gate = dep.get("gate") or "N/A"
    dep_scheduled = dep.get("scheduled") or "Unknown"
    dep_delay = dep.get("delay")
    dep_delay_text = f"{dep_delay} minutes" if dep_delay is not None else "N/A"

    arr_airport = arr.get("airport") or "Unknown arrival airport"
    arr_iata = arr.get("iata") or "Unknown"
    arr_terminal = arr.get("terminal") or "N/A"
    arr_gate = arr.get("gate") or "N/A"
    arr_scheduled = arr.get("scheduled") or "Unknown"
    arr_delay = arr.get("delay")
    arr_delay_text = f"{arr_delay} minutes" if arr_delay is not None else "N/A"

    return f"""
Airline: {airline}
Flight: {flight_number}
Status: {status}

Departure:
- Airport: {dep_airport}
- IATA: {dep_iata}
- Terminal: {dep_terminal}
- Gate: {dep_gate}
- Scheduled: {dep_scheduled}
- Delay: {dep_delay_text}

Arrival:
- Airport: {arr_airport}
- IATA: {arr_iata}
- Terminal: {arr_terminal}
- Gate: {arr_gate}
- Scheduled: {arr_scheduled}
- Delay: {arr_delay_text}
""".strip()


def search_flights(query: str, limit: int = 10):
    """Main entry point: search and format live flight data for a query."""
    if not API_KEY:
        return (
            "Flight API error: AVIATIONSTACK_API_KEY is missing.\n"
            "Please add this in your .env file:\n"
            "AVIATIONSTACK_API_KEY=your_api_key_here"
        )

    dep_iata, arr_iata = parse_route(query)

    params = {
        "access_key": API_KEY,
        "limit": min(limit, 100),
    }

    # Add filters only when a route is identified.

    if dep_iata:
        params["dep_iata"] = dep_iata

    if arr_iata:
        params["arr_iata"] = arr_iata

    try:
        response = requests.get(BASE_URL, params=params, timeout=30)
        data = response.json()
    except requests.exceptions.RequestException as e:
        return f"Flight API request failed: {e}"
    except ValueError:
        return "Flight API returned invalid JSON."

    # Handle API-level errors returned by AviationStack.

    if "error" in data:
        error = data["error"]
        return (
            "Flight API error:\n"
            f"Code: {error.get('code', 'Unknown')}\n"
            f"Message: {error.get('message', 'Unknown error')}"
        )

    flight_data = data.get("data", [])

    if not flight_data:
        route_text = ""

        if dep_iata and arr_iata:
            route_text = f" for route {dep_iata} to {arr_iata}"
        elif dep_iata:
            route_text = f" from {dep_iata}"
        elif arr_iata:
            route_text = f" to {arr_iata}"

        return (
            f"No live flight data found{route_text}.\n\n"
            "Note: AviationStack provides live/status flight data, not ticket prices. "
            "For actual fare prices, use a flight-pricing API such as Amadeus."
        )

    # Build a human-friendly route description for the output.
    route_info = "Global live flights"

    if dep_iata and arr_iata:
        route_info = f"Live flights from {dep_iata} to {arr_iata}"
    elif dep_iata:
        route_info = f"Live flights from {dep_iata}"
    elif arr_iata:
        route_info = f"Live flights to {arr_iata}"

    formatted_flights = [format_flight(flight) for flight in flight_data[:limit]]

    return f"{route_info}\n\n" + "\n\n---\n\n".join(formatted_flights)


if __name__ == "__main__":
    print(search_flights("Plan a 7 days Japan trip from India"))
    print("\n" + "=" * 80 + "\n")
    print(search_flights("all country flight info"))