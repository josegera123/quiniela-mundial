"""
Fetches finished FIFA World Cup 2026 matches from football-data.org
and updates Goles Local Real / Goles Visitante Real in Airtable.

Runs automatically via GitHub Actions twice a day.
Can also be triggered manually from the Actions tab on GitHub.
"""

import os
import sys
import time
import requests
from urllib.parse import quote

FOOTBALL_API_KEY = os.environ["FOOTBALL_API_KEY"]
AIRTABLE_TOKEN   = os.environ["AIRTABLE_TOKEN"]
AIRTABLE_BASE    = "appH8ihJul8pDWOmE"
COMPETITION      = "WC"   # FIFA World Cup code on football-data.org

AT_HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json",
}

# football-data.org English names → Airtable Spanish names
TEAM_MAP = {
    "Mexico":                  "México",
    "South Africa":            "Sudáfrica",
    "Korea Republic":          "Corea del Sur",
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
}


def translate(name: str) -> str:
    return TEAM_MAP.get(name, name)


def fetch_finished_matches() -> list:
    url = f"https://api.football-data.org/v4/competitions/{COMPETITION}/matches"
    resp = requests.get(
        url,
        headers={"X-Auth-Token": FOOTBALL_API_KEY},
        params={"status": "FINISHED"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("matches", [])


def find_airtable_record(home_es: str, away_es: str) -> dict | None:
    formula = f'AND({{Equipo Local}}="{home_es}",{{Equipo Visitante}}="{away_es}")'
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE}/{quote('Partidos')}"
    resp = requests.get(url, headers=AT_HEADERS, params={"filterByFormula": formula}, timeout=15)
    resp.raise_for_status()
    records = resp.json().get("records", [])
    return records[0] if records else None


def update_airtable_record(record_id: str, home_score: int, away_score: int) -> None:
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE}/{quote('Partidos')}/{record_id}"
    payload = {
        "fields": {
            "Goles Reales Local":     str(home_score),
            "Goles Reales Visitante": str(away_score),
        }
    }
    resp = requests.patch(url, headers=AT_HEADERS, json=payload, timeout=15)
    if not resp.ok:
        print(f"  Airtable error body: {resp.text}")
    resp.raise_for_status()


def main() -> None:
    print("⚽ Fetching finished World Cup 2026 matches...")
    try:
        matches = fetch_finished_matches()
    except requests.HTTPError as e:
        print(f"❌ football-data.org error: {e}")
        sys.exit(1)

    print(f"   Found {len(matches)} finished match(es)\n")

    updated = 0
    skipped = 0
    errors  = 0

    for match in matches:
        home_raw   = match["homeTeam"]["name"]
        away_raw   = match["awayTeam"]["name"]
        home_score = match["score"]["fullTime"]["home"]
        away_score = match["score"]["fullTime"]["away"]

        if home_score is None or away_score is None:
            continue

        home_es = translate(home_raw)
        away_es = translate(away_raw)

        print(f"{home_es} {home_score} – {away_score} {away_es}")

        try:
            record = find_airtable_record(home_es, away_es)
        except requests.HTTPError as e:
            print(f"  ⚠️  Airtable lookup failed: {e}")
            errors += 1
            continue

        if not record:
            print(f"  ⚠️  No Airtable record found (check team name mapping)")
            skipped += 1
            continue

        fields = record["fields"]
        already_correct = (
            fields.get("Goles Reales Local")     == str(home_score) and
            fields.get("Goles Reales Visitante") == str(away_score)
        )
        if already_correct:
            print("  ✓  Already up to date")
            continue

        try:
            update_airtable_record(record["id"], home_score, away_score)
            print("  ✅ Updated")
            updated += 1
        except requests.HTTPError as e:
            print(f"  ❌ Update failed: {e}")
            errors += 1

        time.sleep(0.25)  # stay within Airtable rate limits

    print(f"\nDone — updated: {updated} | skipped: {skipped} | errors: {errors}")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
