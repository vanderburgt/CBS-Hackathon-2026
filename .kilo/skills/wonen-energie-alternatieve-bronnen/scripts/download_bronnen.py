#!/usr/bin/env python3
"""Download open bronnen voor wonen- en energieonderzoek naar een lokale map.

Haalt twee soorten bronnen binnen en slaat ze op in `data/`, zodat de rest van
de analyse offline werkt — ook als een API tijdens de hackathon uitvalt:

1. Netbeheerdata kleinverbruik (Liander), TSV met `.csv`-extensie, per PC6.
2. PDOK CBS wijk- en buurtkaart (kerncijfers per buurt/wijk/gemeente) als GeoJSON,
   met of zonder geometrie. Met geometrie is nodig voor de ruimtelijke PC6-koppeling.

Alleen afhankelijk van de standaardbibliotheek (urllib). Geen pandas/requests nodig,
zodat dit script in elke omgeving draait.

Gebruik:
    python download_bronnen.py --out data
    python download_bronnen.py --out data --pdok-jaar 2023 --pdok-niveau buurten
    python download_bronnen.py --out data --pdok-jaar 2024 --met-geometrie
    python download_bronnen.py --out data --liander-jaar 2025

Alle stappen loggen naar stdout en naar `data/download_log.txt`. Eén mislukte bron
stopt de rest niet; aan het eind volgt een samenvatting.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# De PDOK-WFS levert maximaal 1000 features per request, ongeacht COUNT. Pagineer
# daarom met deze paginagrootte en STARTINDEX.
PDOK_PAGE = 1000

# Geverifieerd op 2026-06-30 (HTTP 200). Controleer de URL bij gebruik; netbeheerders
# wijzigen padnamen per jaargang.
LIANDER_URLS = {
    "2025": "https://www.liander.nl/-/media/files/open-data/kleinverbruikdata/verbruiksdata-kv-2025in.csv",
    "2026": "https://www.liander.nl/-/media/files/open-data/kleinverbruikdata/verbruiksdata-kv-2026.csv",
}

PDOK_WFS = "https://service.pdok.nl/cbs/wijkenbuurten/{jaar}/wfs/v1_0"
PDOK_NIVEAUS = {"buurten", "wijken", "gemeenten"}

# Attributen die voor wonen-energie-analyses relevant zijn. Niet elke kolom is in
# elke jaargang gevuld — zie references/kolomnamen.md voor de jaarmatrix.
PDOK_PROPS = (
    "buurtcode,buurtnaam,wijkcode,gemeentecode,gemeentenaam,water,"
    "meestVoorkomendePostcode,woningvoorraad,aantalInwoners,aantalHuishoudens,"
    "gemiddeldeWoningwaarde,percentageEengezinswoning,percentageMeergezinswoning,"
    "percentageKoopwoningen,percentageHuurwoningen,"
    "percHuurwoningenInBezitWoningcorporaties,percHuurwoningenInBezitOverigeVerhuurders,"
    "gemiddeldAardgasverbruik,gemiddeldGasverbruikHuurwoning,gemiddeldGasverbruikkoopwoning,"
    "gemiddeldGasverbruikAppartement,gemiddeldGasverbruikTussenwoning,"
    "gemiddeldGasverbruikVrijstaandeWoning,gemiddeldeElektriciteitslevering,"
    "percentageWoningenMetZonnestroom,percentageAardgasvrijeWoningen,"
    "percentageAardgaswoningen,percentageWoningenMetStadsverwarming,"
    "mediaanVermogenVanParticuliereHuish,omgevingsadressendichtheid"
)

LOG_LINES: list[str] = []


def log(msg: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
    line = f"[{stamp}] {msg}"
    print(line, flush=True)
    LOG_LINES.append(line)


def _request(url: str, timeout: int = 120) -> bytes:
    req = Request(url, headers={"User-Agent": "wonen-energie-skill/1.0"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()


def download_liander(jaar: str, out: Path) -> bool:
    url = LIANDER_URLS.get(jaar)
    if not url:
        log(f"Liander {jaar}: geen bekende URL. Beschikbaar: {sorted(LIANDER_URLS)}. "
            f"Zie references/bronnen.md voor de open-data pagina.")
        return False
    doel = out / f"liander_{jaar}.tsv"
    log(f"Liander {jaar}: download {url}")
    try:
        data = _request(url)
    except (HTTPError, URLError, TimeoutError) as e:
        log(f"Liander {jaar}: MISLUKT ({e}).")
        return False
    doel.write_bytes(data)
    regels = data.count(b"\n")
    log(f"Liander {jaar}: opgeslagen als {doel.name} ({len(data)/1e6:.1f} MB, {regels} regels).")
    return True


def _geldige_velden(base: str, typename: str) -> set[str]:
    """Haal via DescribeFeatureType de geldige attribuutnamen voor deze jaargang op.

    De WFS weigert het hele GetFeature-verzoek (HTTP 400) als ook maar één
    PROPERTYNAME niet bestaat. Kolommen verschillen per jaar (zon en aardgasvrij
    zitten bijv. alleen in 2024), dus filteren we de gewenste lijst tegen wat er is.
    """
    params = {"SERVICE": "WFS", "VERSION": "2.0.0",
              "REQUEST": "DescribeFeatureType", "TYPENAMES": typename}
    try:
        raw = _request(f"{base}?{urlencode(params)}", timeout=60)
    except (HTTPError, URLError, TimeoutError) as e:
        log(f"PDOK DescribeFeatureType mislukt ({e}); ga door zonder veldfiltering.")
        return set()
    return set(re.findall(r'name="([a-zA-Z0-9]+)"', raw.decode("utf-8", "replace")))


def download_pdok(jaar: str, niveau: str, out: Path, met_geometrie: bool) -> bool:
    if niveau not in PDOK_NIVEAUS:
        log(f"PDOK: onbekend niveau '{niveau}'. Kies uit {sorted(PDOK_NIVEAUS)}.")
        return False
    base = PDOK_WFS.format(jaar=jaar)
    typename = f"wijkenbuurten:{niveau}"
    log(f"PDOK {niveau} {jaar}: ophalen via WFS ({'met' if met_geometrie else 'zonder'} geometrie)")

    props = None
    if not met_geometrie:
        gewenst = PDOK_PROPS.split(",")
        beschikbaar = _geldige_velden(base, typename)
        if beschikbaar:
            geldig = [c for c in gewenst if c in beschikbaar]
            weg = [c for c in gewenst if c not in beschikbaar]
            if weg:
                log(f"PDOK {niveau} {jaar}: niet in deze jaargang, overgeslagen: {', '.join(weg)}")
            props = ",".join(geldig)

    features: list[dict] = []
    start = 0
    while True:
        params = {
            "SERVICE": "WFS",
            "VERSION": "2.0.0",
            "REQUEST": "GetFeature",
            "TYPENAMES": typename,
            "OUTPUTFORMAT": "application/json",
            "COUNT": str(PDOK_PAGE),
            "STARTINDEX": str(start),
        }
        if props:
            params["PROPERTYNAME"] = props
        url = f"{base}?{urlencode(params)}"
        try:
            raw = _request(url)
        except (HTTPError, URLError, TimeoutError) as e:
            log(f"PDOK {niveau} {jaar}: MISLUKT bij startindex {start} ({e}).")
            return False
        if raw.lstrip().startswith(b"<"):
            # WFS-foutmelding komt als XML terug.
            log(f"PDOK {niveau} {jaar}: WFS-fout: {raw[:300].decode('utf-8', 'replace')}")
            return False
        batch = json.loads(raw).get("features", [])
        if not met_geometrie:
            # PROPERTYNAME beperkt de attributen, maar de WFS levert de geometrie tóch.
            # Strip die om de bestandsomvang klein te houden.
            for f in batch:
                f.pop("geometry", None)
                f.pop("bbox", None)
        features.extend(batch)
        log(f"PDOK {niveau} {jaar}: {len(features)} features opgehaald...")
        if len(batch) < PDOK_PAGE:
            break
        start += PDOK_PAGE
        time.sleep(0.3)

    suffix = "_geo" if met_geometrie else ""
    doel = out / f"pdok_{niveau}_{jaar}{suffix}.geojson"
    doel.write_text(json.dumps({"type": "FeatureCollection", "features": features}),
                    encoding="utf-8")
    log(f"PDOK {niveau} {jaar}: opgeslagen als {doel.name} ({len(features)} features, "
        f"{'incl.' if met_geometrie else 'zonder'} geometrie).")
    return True


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Download open bronnen wonen/energie naar data/.")
    p.add_argument("--out", default="data", help="Doelmap (default: data)")
    p.add_argument("--liander-jaar", default="2025", help="Liander-jaargang (default: 2025)")
    p.add_argument("--geen-liander", action="store_true", help="Sla netbeheerdata over")
    p.add_argument("--pdok-jaar", default="2024",
                   help="PDOK-jaargang. 2023 heeft gas per woningtype; 2024 heeft zon/aardgasvrij. Default: 2024")
    p.add_argument("--pdok-niveau", default="buurten",
                   help="buurten | wijken | gemeenten (default: buurten)")
    p.add_argument("--geen-pdok", action="store_true", help="Sla PDOK-buurtkaart over")
    p.add_argument("--met-geometrie", action="store_true",
                   help="Download PDOK inclusief polygonen (nodig voor ruimtelijke PC6-koppeling)")
    args = p.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    resultaten: dict[str, bool] = {}
    if not args.geen_liander:
        resultaten[f"liander_{args.liander_jaar}"] = download_liander(args.liander_jaar, out)
    if not args.geen_pdok:
        resultaten[f"pdok_{args.pdok_niveau}_{args.pdok_jaar}"] = download_pdok(
            args.pdok_jaar, args.pdok_niveau, out, args.met_geometrie)

    log("=== Samenvatting ===")
    for naam, ok in resultaten.items():
        log(f"  {'OK ' if ok else 'FOUT'}  {naam}")
    (out / "download_log.txt").write_text("\n".join(LOG_LINES) + "\n", encoding="utf-8")

    # Exitcode 1 als minstens één bron mislukte, zodat een agent dit kan detecteren.
    return 0 if all(resultaten.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
