"""
Fetches upcoming FIFA World Cup 2026 matches from football-data.org
and creates missing records in the Airtable Partidos table.

Run manually:
  FOOTBALL_API_KEY=... AIRTABLE_TOKEN=... python scripts/populate_matches.py

Or trigger from the GitHub Actions tab (workflow_dispatch).
"""

import os
import sys
import time
import requests
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

FOOTBALL_API_KEY = os.environ["FOOTBALL_API_KEY"]
AIRTABLE_TOKEN   = os.environ["AIRTABLE_TOKEN"]
AIRTABLE_BASE    = "appH8ihJul8pDWOmE"
COMPETITION      = "WC"

GUATEMALA_TZ = timezone(timedelta(hours=-6))

AT_HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json",
}

TEAM_MAP = {
    "Mexico":                  "México",
    "South Africa":            "Sudáfrica",
    "Korea Republic":          "Corea del Sur",
    "South Korea":             "Corea del Sur",
    "Czechia":                 "Chequia",
    "Czech Republic":          "Chequia",
    "Canada":                  "Canadá",
    "Bosnia and Herzegovina":  "Bosnia y Herzegovina",
    "Qatar":                   "Catar",
    "Switzerland":             "Suiza",
    "United States":           "Estados Unidos",
    "Paraguay":                "Paraguay",
    "Brazil":                  "Brasil",
    "Morocco":                 "Marruecos",
    "Haiti":                   "Haití",
    "Scotland":                "Escocia",
    "Australia":               "Australia",
    "Turkey":                  "Turquía",
    "Türkiye":                 "Turquía",
    "Germany":                 "Alemania",
    "Curaçao":                 "Curazao",
    "Curacao":                 "Curazao",
    "Netherlands":             "Países Bajos",
    "Japan":                   "Japón",
    "Côte d'Ivoire":           "Costa de Marfil",
    "Ivory Coast":             "Costa de Marfil",
    "Ecuador":                 "Ecuador",
    "Sweden":                  "Suecia",
    "Tunisia":                 "Túnez",
    "Spain":                   "España",
    "Cape Verde":              "Cabo Verde",
    "Belgium":                 "Bélgica",
    "Egypt":                   "Egipto",
    "Saudi Arabia":            "Arabia Saudita",
    "Uruguay":                 "Uruguay",
    "Iran":                    "Irán",
    "New Zealand":             "Nueva Zelanda",
    "France":                  "Francia",
    "Senegal":                 "Senegal",
    "Iraq":                    "Irak",
    "Norway":                  "Noruega",
    "Argentina":               "Argentina",
    "Algeria":                 "Argelia",
    "Austria":                 "Austria",
    "Jordan":                  "Jordania",
    "Portugal":                "Portugal",
    "Congo":                   "República del Congo",
    "DR Congo":                "República del Congo",
    "England":                 "Inglaterra",
    "Croatia":                 "Croacia",
    "Ghana":                   "Ghana",
    "Panama":                  "Panamá",
    "Uzbekistan":              "Uzbekistán",
    "Colombia":                "Colombia",
    "Venezuela":               "Venezuela",
    "Chile":                   "Chile",
    "Peru":                    "Perú",
    "Bolivia":                 "Bolivia",
    "Costa Rica":              "Costa Rica",
    "Honduras":                "Honduras",
    "Guatemala":               "Guatemala",
    "El Salvador":             "El Salvador",
    "Jamaica":                 "Jamaica",
    "Trinidad and Tobago":     "Trinidad y Tobago",
    "Cuba":                    "Cuba",
    "Nigeria":                 "Nigeria",
    "Cameroon":                "Camerún",
    "Zambia":                  "Zambia",
    "Tanzania":                "Tanzania",
    "Zimbabwe":                "Zimbabue",
    "Angola":                  "Angola",
    "Kenya":                   "Kenia",
    "Romania":                 "Rumania",
    "Ukraine":                 "Ucrania",
    "Serbia":                  "Serbia",
    "Hungary":                 "Hungría",
    "Greece":                  "Grecia",
    "Poland":                  "Polonia",
    "Denmark":                 "Dinamarca",
    "Albania":                 "Albania",
    "Slovakia":                "Eslovaquia",
    "Slovenia":                "Eslovenia",
    "China PR":                "China",
    "China":                   "China",
    "Indonesia":               "Indonesia",
    "Thailand":                "Tailandia",
    "Vietnam":                 "Vietnam",
    "Bahrain":                 "Baréin",
    "Oman":                    "Omán",
    "United Arab Emirates":    "Emiratos Árabes Unidos",
    "Kuwait":                  "Kuwait",
    "Palestine":               "Palestina",
    "Israel":                  "Israel",
}

STAGE_MAP = {
    "GROUP_STAGE":    "Fase de Grupos",
    "LAST_32":        "Dieciseisavos de Final",
    "ROUND_OF_32":    "Dieciseisavos de Final",
    "ROUND_OF_16":    "Octavos de Final",
    "LAST_16":        "Octavos de Final",
    "QUARTER_FINALS": "Cuartos de Final",
    "SEMI_FINALS":    "Semifinal",
    "THIRD_PLACE":    "Tercer Puesto",
    "FINAL":          "Final",
}


def translate(name: str) -> str:
    return TEAM_MAP.get(name, name)


def fetch_matches(status: str) -> list:
    url = f"https://api.football-data.org/v4/competitions/{COMPETITION}/matches"
    resp = requests.get(
        url,
        headers={"X-Auth-Token": FOOTBALL_API_KEY},
        params={"status": status},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("matches", [])


def record_exists(home_es: str, away_es: str) -> bool:
    formula = f'AND({{Equipo Local}}="{home_es}",{{Equipo Visitante}}="{away_es}")'
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE}/{quote('Partidos')}"
    resp = requests.get(url, headers=AT_HEADERS, params={"filterByFormula": formula}, timeout=15)
    resp.raise_for_status()
    return len(resp.json().get("records", [])) > 0


def utc_to_guatemala(utc_str: str) -> str:
    dt_utc = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
    dt_gt  = dt_utc.astimezone(GUATEMALA_TZ)
    return dt_gt.strftime("%Y-%m-%dT%H:%M:%S")


def create_record(home_es: str, away_es: str, fecha_gt: str, fase: str) -> None:
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE}/{quote('Partidos')}"
    payload = {
        "fields": {
            "Equipo Local":             home_es,
            "Equipo Visitante":         away_es,
            "Fecha y Hora (Guatemala)": fecha_gt,
            "Fase":                     fase,
        }
    }
    resp = requests.post(url, headers=AT_HEADERS, json=payload, timeout=15)
    if not resp.ok:
        print(f"  Airtable error: {resp.text}")
    resp.raise_for_status()


def main() -> None:
    # Fetch both scheduled and in-progress bracket matches
    print("⚽ Fetching upcoming World Cup 2026 matches...")
    try:
        matches = fetch_matches("SCHEDULED") + fetch_matches("TIMED")
    except requests.HTTPError as e:
        print(f"❌ football-data.org error: {e}")
        sys.exit(1)

    # All knockout stages (skip group stage — those are already in Airtable)
    bracket_stages = {
        "LAST_32", "ROUND_OF_32",
        "LAST_16", "ROUND_OF_16",
        "QUARTER_FINALS",
        "SEMI_FINALS",
        "THIRD_PLACE",
        "FINAL",
    }
    matches = [m for m in matches if m.get("stage") in bracket_stages]

    print(f"   Found {len(matches)} bracket match(es)\n")

    created = 0
    skipped = 0
    errors  = 0

    for match in matches:
        home_raw = match["homeTeam"]["name"]
        away_raw = match["awayTeam"]["name"]
        stage    = match.get("stage", "")
        utc_date = match.get("utcDate", "")

        # Skip matches where teams haven't been determined yet
        if not home_raw or not away_raw:
            print(f"{STAGE_MAP.get(stage, stage)}: equipos aún por definir — omitido")
            skipped += 1
            continue

        home_es = translate(home_raw)
        away_es = translate(away_raw)
        fase    = STAGE_MAP.get(stage, stage)
        fecha   = utc_to_guatemala(utc_date) if utc_date else ""

        print(f"{fase}: {home_es} vs {away_es}  ({fecha} GT)")

        # TBD matches (placeholder teams like "Winner Group A") are kept as-is
        try:
            if record_exists(home_es, away_es):
                print("  ✓  Ya existe en Airtable")
                skipped += 1
            else:
                create_record(home_es, away_es, fecha, fase)
                print("  ✅ Creado en Airtable")
                created += 1
        except requests.HTTPError as e:
            print(f"  ❌ Error: {e}")
            errors += 1

        time.sleep(0.25)

    print(f"\nDone — creados: {created} | ya existían: {skipped} | errores: {errors}")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
