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


# Each source: a World Bank indicator mirrored by the datahub `datasets` org.
SOURCES = [
    {
        "name": "population",
        "domain": "demografi",
        "metric": "nüfus",
        "unit": "kişi",
        "csv_url": "https://raw.githubusercontent.com/datasets/population/main/data/population.csv",
        "datapackage_url": "https://raw.githubusercontent.com/datasets/population/main/datapackage.json",
        "code_column": "Country Code",
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
        "datapackage_url": "https://raw.githubusercontent.com/datasets/gdp/main/datapackage.json",
        "code_column": "Country Code",
        "year_column": "Year",
        "value_column": "Value",
        "value_is_int": True,
    },
    {
        "name": "inflation",
        "domain": "ekonomi",
        "metric": "enflasyon oranı",
        "unit": "yüzde",
        "csv_url": "https://raw.githubusercontent.com/datasets/inflation/main/data/inflation-gdp.csv",
        "datapackage_url": "https://raw.githubusercontent.com/datasets/inflation/main/datapackage.json",
        "code_column": "Country Code",
        "year_column": "Year",
        "value_column": "Inflation",
        "value_is_int": False,
    },
]


def http_get(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "TR-DataAnalystBench/real-fetch"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def fetch_license(datapackage_url: str) -> dict:
    try:
        data = json.loads(http_get(datapackage_url))
    except Exception as error:  # noqa: BLE001 - provenance is best-effort
        return {"name": "unknown", "error": str(error)}

    licenses = data.get("licenses") or data.get("license")
    if isinstance(licenses, list) and licenses:
        return licenses[0]
    if isinstance(licenses, str):
        return {"name": licenses}
    return {"name": "unknown"}


def extract_country_rows(csv_text: str, source: dict) -> list[tuple[int, float]]:
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = []
    for record in reader:
        if record.get(source["code_column"]) != COUNTRY_CODE:
            continue
        raw_value = record.get(source["value_column"], "").strip()
        raw_year = record.get(source["year_column"], "").strip()
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
        license_info = fetch_license(source["datapackage_url"])

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
            "indicator_source": "World Bank (via datahub datasets mirror)",
            "url": source["csv_url"],
            "license": license_info,
            "rows": len(rows),
            "year_min": rows[0][0] if rows else None,
            "year_max": rows[-1][0] if rows else None,
            "local_path": str(out_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        })

        print(f"  {len(rows)} rows ({rows[0][0]}-{rows[-1][0]}), license: {license_info.get('name')}")

    PROVENANCE_PATH.write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nProvenance written to {PROVENANCE_PATH}")


if __name__ == "__main__":
    main()
