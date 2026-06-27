"""Fetch real, redistributable open-data sources for the real-data tier.

Downloads a small set of World Bank indicators (via the datahub `datasets`
mirrors on GitHub) for Türkiye, caches them locally under data/sources_real/,
and records provenance + license for each source. The generator reads the
local cache, so dataset generation is reproducible without network access.

Only GitHub-hosted (raw.githubusercontent.com) sources are used because that
is what this environment can reach.
"""

import csv
import io
import json
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCES_DIR = PROJECT_ROOT / "data" / "sources_real"
SOURCES_DIR.mkdir(parents=True, exist_ok=True)

PROVENANCE_PATH = SOURCES_DIR / "provenance.json"

COUNTRY_CODE = "TUR"
COUNTRY_LABEL = "Türkiye"


# Each source is a redistributable, GitHub-hosted open dataset that contains
# yearly values for Türkiye. Country rows are matched either by ISO code
# ("code" mode) or by country name ("name" mode). Licenses are recorded
# explicitly because not every source ships a datapackage.json.
SOURCES = [
    {
        "name": "population",
        "domain": "demografi",
        "metric": "nüfus",
        "unit": "kişi",
        "csv_url": "https://raw.githubusercontent.com/datasets/population/main/data/population.csv",
        "source_title": "World Bank (datahub datasets mirror)",
        "license": {"name": "ODC-PDDL-1.0"},
        "match_mode": "code",
        "match_column": "Country Code",
        "match_value": "TUR",
        "year_column": "Year",
        "value_column": "Value",
        "value_is_int": True,
    },
    {
        "name": "gdp",
        "domain": "ekonomi",
        "metric": "gayrisafi yurt içi hasıla",
        "unit": "dolar",
        "csv_url": "https://raw.githubusercontent.com/datasets/gdp/main/data/gdp.csv",
        "source_title": "World Bank (datahub datasets mirror)",
        "license": {"name": "CC-BY-4.0"},
        "match_mode": "code",
        "match_column": "Country Code",
        "match_value": "TUR",
        "year_column": "Year",
        "value_column": "Value",
        "value_is_int": True,
    },
    {
        "name": "inflation",
        "domain": "ekonomi",
        "metric": "tüketici enflasyon oranı",
        "unit": "yüzde",
        "csv_url": "https://raw.githubusercontent.com/datasets/inflation/main/data/inflation-consumer.csv",
        "source_title": "World Bank consumer price inflation (datahub datasets mirror)",
        "license": {"name": "ODC-PDDL-1.0"},
        "match_mode": "code",
        "match_column": "Country Code",
        "match_value": "TUR",
        "year_column": "Year",
        "value_column": "Inflation",
        "value_is_int": False,
    },
    {
        "name": "co2",
        "domain": "çevre",
        "metric": "fosil yakıt CO2 salımı",
        "unit": "bin ton karbon",
        "csv_url": "https://raw.githubusercontent.com/datasets/co2-fossil-by-nation/master/data/fossil-fuel-co2-emissions-by-nation.csv",
        "source_title": "CDIAC fossil-fuel CO2 emissions by nation (datahub datasets mirror)",
        "license": {"name": "ODC-PDDL-1.0"},
        "match_mode": "name",
        "match_column": "Country",
        "match_value": "TURKEY",
        "year_column": "Year",
        "value_column": "Total",
        "value_is_int": True,
    },
    # NOTE: OWID energy-data (enerji) would add an "enerji" domain, but its CSV
    # is ~9 MB and is truncated by the proxy in this environment. Add it (or a
    # smaller energy source) when a reliably fetchable file is available.
]


def http_get(url: str, attempts: int = 4) -> str:
    """GET with retries; large files over the proxy occasionally truncate."""
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "TR-DataAnalystBench/real-fetch"}
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                expected = response.length  # bytes still to read, if advertised
                data = response.read()
            if expected and len(data) < expected:
                raise IOError(f"short read: got {len(data)} of {expected} bytes")
            return data.decode("utf-8", errors="replace")
        except Exception as error:  # noqa: BLE001 - retry any transient failure
            last_error = error
            print(f"  attempt {attempt}/{attempts} failed: {error}")
    raise RuntimeError(f"Failed to fetch {url}: {last_error}")


def matches_country(record: dict, source: dict) -> bool:
    cell = (record.get(source["match_column"]) or "").strip()
    if source["match_mode"] == "code":
        return cell == source["match_value"]
    # name mode: case-insensitive exact match
    return cell.lower() == source["match_value"].lower()


def extract_country_rows(csv_text: str, source: dict) -> list[tuple[int, float]]:
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = []
    for record in reader:
        if not matches_country(record, source):
            continue
        raw_value = (record.get(source["value_column"]) or "").strip()
        raw_year = (record.get(source["year_column"]) or "").strip()
        if not raw_value or not raw_year:
            continue
        try:
            year = int(float(raw_year))
            value = float(raw_value)
        except ValueError:
            continue
        if source["value_is_int"]:
            value = int(round(value))
        else:
            value = round(value, 2)
        rows.append((year, value))

    rows.sort(key=lambda r: r[0])
    return rows


def main() -> None:
    provenance = {
        "country_code": COUNTRY_CODE,
        "country_label": COUNTRY_LABEL,
        "note": "Real open data cached locally for reproducible generation.",
        "sources": [],
    }

    for source in SOURCES:
        print(f"Fetching {source['name']} ...")
        csv_text = http_get(source["csv_url"])
        rows = extract_country_rows(csv_text, source)

        if not rows:
            raise ValueError(f"No rows extracted for {source['name']} — check match config")

        out_path = SOURCES_DIR / f"{source['name']}.csv"
        with out_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Year", "Value"])
            writer.writerows(rows)

        provenance["sources"].append({
            "name": source["name"],
            "domain": source["domain"],
            "metric": source["metric"],
            "unit": source["unit"],
            "indicator_source": source["source_title"],
            "url": source["csv_url"],
            "license": source["license"],
            "rows": len(rows),
            "year_min": rows[0][0],
            "year_max": rows[-1][0],
            "local_path": str(out_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        })

        print(f"  {len(rows)} rows ({rows[0][0]}-{rows[-1][0]}), license: {source['license'].get('name')}")

    PROVENANCE_PATH.write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nProvenance written to {PROVENANCE_PATH}")


if __name__ == "__main__":
    main()
