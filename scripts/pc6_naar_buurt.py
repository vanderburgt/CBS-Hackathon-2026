#!/usr/bin/env python3
"""Koppel netbeheerdata (PC6) aan CBS-buurten.

Netbeheerdata zit op postcode-6 niveau, alle andere bronnen op buurt/wijk/gemeente.
Er bestaat geen altijd-beschikbare PC6→buurt crosswalk buiten CBS StatLine om, dus
dit script biedt drie routes (zie references/geo-koppeling.md):

  via_pc4        Snelle benadering via de eerste 4 cijfers van de postcode, gekoppeld
                 aan PDOK-veld `meestVoorkomendePostcode`. Alleen pandas nodig. Werkt
                 altijd, maar grof: meerdere buurten kunnen dezelfde PC4 delen.
  ruimtelijk     Nauwkeurig: PC6-centroide via PDOK Locatieserver + point-in-polygon
                 op de PDOK-buurtpolygonen. Vereist geopandas en een GeoJSON mét
                 geometrie (download met `download_bronnen.py --met-geometrie`).
  crosswalk      Nauwkeurigst: CBS pc6hnr-koppeltabel, als die lokaal beschikbaar is.

Bevat ook `laad_liander()` voor het lezen van het netbeheer-TSV-formaat (regels met
buitenste aanhalingstekens, tab-gescheiden, ondanks de .csv-extensie).

Gebruik als module:
    from pc6_naar_buurt import laad_liander, koppel_pc6_via_pc4
    gas = laad_liander("data/liander_2025.tsv", productsoort="GAS")
    gekoppeld = koppel_pc6_via_pc4(gas, "data/pdok_buurten_2024.geojson")

Gebruik als script:
    python pc6_naar_buurt.py --liander data/liander_2025.tsv --pdok data/pdok_buurten_2024.geojson \
        --route pc4 --productsoort GAS --uit data/gas_per_buurt.csv
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

SENTINELS = (-99997, -99998, -99995, -99997.0, -99998.0, -99995.0)
LOCATIESERVER = "https://api.pdok.nl/bzk/locatieserver/search/v3_1"


# --------------------------------------------------------------------------- #
# Inlezen netbeheerdata
# --------------------------------------------------------------------------- #
def laad_liander(pad: str | Path, productsoort: str | None = None) -> pd.DataFrame:
    """Lees een Liander-kleinverbruikbestand (geverifieerd formaat 2025).

    Elke regel is omhuld door buitenste aanhalingstekens en intern tab-gescheiden.
    `SJA GEMIDDELD` (met spatie) wordt hernoemd naar `SJA_GEMIDDELD`.
    Filtert optioneel op PRODUCTSOORT ('GAS' of 'ELK').
    """
    with open(pad, encoding="utf-8") as f:
        schoon = "\n".join(line.strip().strip('"') for line in f if line.strip())
    df = pd.read_csv(
        io.StringIO(schoon),
        sep="\t",
        dtype={"POSTCODE": str, "POSTCODE_EIND": str},
    )
    df = df.rename(columns={"SJA GEMIDDELD": "SJA_GEMIDDELD"})
    if productsoort:
        df = df[df["PRODUCTSOORT"] == productsoort].copy()
    df["PC6"] = df["POSTCODE"].str.replace(" ", "").str.upper()
    df["PC4"] = df["PC6"].str[:4]
    return df


# --------------------------------------------------------------------------- #
# PDOK-buurtkaart inlezen
# --------------------------------------------------------------------------- #
def laad_pdok_attributen(geojson_pad: str | Path) -> pd.DataFrame:
    """Lees een PDOK-buurt GeoJSON als platte attributentabel (zonder geometrie)."""
    data = json.loads(Path(geojson_pad).read_text(encoding="utf-8"))
    rijen = [f["properties"] for f in data.get("features", [])]
    df = pd.DataFrame(rijen)
    if "water" in df.columns:
        df = df[df["water"] == "NEE"].copy()  # let op: 'NEE', niet 'N'
    return df


# --------------------------------------------------------------------------- #
# Route 1: PC4-benadering (alleen pandas)
# --------------------------------------------------------------------------- #
def koppel_pc6_via_pc4(
    net: pd.DataFrame,
    pdok_geojson: str | Path,
    waarde_kolom: str = "SJA_GEMIDDELD",
    pc6_kolom: str = "PC6",
) -> pd.DataFrame:
    """Aggregeer netbeheerdata per PC4 en koppel aan buurten via `meestVoorkomendePostcode`.

    Grove benadering: gebruik voor oriëntatie, niet voor publicatie. Retourneert per
    buurt het PC4-gemiddelde van `waarde_kolom` plus de PDOK-buurtattributen.
    """
    buurten = laad_pdok_attributen(pdok_geojson)
    if "meestVoorkomendePostcode" not in buurten.columns:
        raise ValueError("PDOK-bestand mist 'meestVoorkomendePostcode'.")
    buurten["meestVoorkomendePostcode"] = pd.to_numeric(
        buurten["meestVoorkomendePostcode"], errors="coerce")
    buurten = buurten[~buurten["meestVoorkomendePostcode"].isin(SENTINELS)]
    buurten["PC4"] = buurten["meestVoorkomendePostcode"].astype("Int64").astype(str)

    net = net.copy()
    net["PC4"] = net[pc6_kolom].str[:4]
    per_pc4 = (net.groupby("PC4")[waarde_kolom]
               .mean()
               .rename(f"{waarde_kolom}_pc4_gem")
               .reset_index())

    gekoppeld = buurten.merge(per_pc4, on="PC4", how="left")
    return gekoppeld


# --------------------------------------------------------------------------- #
# Route 2: Ruimtelijke koppeling (geopandas + PDOK Locatieserver)
# --------------------------------------------------------------------------- #
def _pc6_centroide(pc6: str, cache: dict[str, tuple[float, float]]) -> tuple[float, float] | None:
    """Zoek lon/lat-centroide van een PC6 via de PDOK Locatieserver (met cache)."""
    if pc6 in cache:
        return cache[pc6]
    try:
        q = urlencode({"q": pc6, "rows": 1, "fl": "centroide_ll", "fq": "type:postcode"})
        req = Request(f"{LOCATIESERVER}/free?{q}",
                      headers={"User-Agent": "wonen-energie-skill/1.0"})
        with urlopen(req, timeout=20) as resp:
            docs = json.loads(resp.read())["response"]["docs"]
        if not docs:
            cache[pc6] = None
            return None
        wkt = docs[0]["centroide_ll"]  # 'POINT(4.90 52.37)'
        lon, lat = wkt.replace("POINT(", "").rstrip(")").split()
        cache[pc6] = (float(lon), float(lat))
    except Exception:
        cache[pc6] = None
    return cache[pc6]


def koppel_pc6_ruimtelijk(
    net: pd.DataFrame,
    buurten_geojson: str | Path,
    pc6_kolom: str = "PC6",
    pauze: float = 0.05,
) -> pd.DataFrame:
    """Koppel elke PC6 aan de buurt waarin de centroide valt (point-in-polygon).

    Vereist geopandas/shapely en een GeoJSON *met* geometrie. Trager (één
    Locatieserver-call per unieke PC6, met cache), maar nauwkeurig en zonder
    externe crosswalk.
    """
    try:
        import geopandas as gpd
        from shapely.geometry import Point
    except ImportError as e:
        raise ImportError(
            "koppel_pc6_ruimtelijk vereist geopandas en shapely. "
            "Installeer met `uv pip install geopandas shapely` of gebruik route 'pc4'."
        ) from e

    buurten = gpd.read_file(buurten_geojson)
    # GeoJSON wordt door geopandas default als EPSG:4326 (WGS84) gelabeld, ook als er
    # geen crs-lid in staat. PDOK levert echter native EPSG:28992 (RD New, meters)
    # tenzij je SRSNAME=EPSG:4326 vraagt — en download_bronnen.py deed dat voorheen
    # niet. Vertrouw dus niet op het gelabelde CRS, maar op de coördinaatgrootte:
    # RD-New-coördinaten zijn ~10^4-10^5, WGS84 graden < 180. Corrigeer een verkeerd
    # label zodat de point-in-polygon-join met WGS84 PC6-centroïden klopt.
    sample_x = abs(buurten.geometry.iloc[0].representative_point().x) if len(buurten) else 0.0
    is_rd = sample_x > 1000
    if is_rd:
        # Het gelabelde CRS (4326) klopt niet voor deze coördinaten — stel RD New in
        # en reprojecteer daarna naar WGS84.
        buurten = buurten.set_crs(epsg=28992, allow_override=True).to_crs(epsg=4326)
        print("Let op: buurten-GeoJSON zat in EPSG:28992 (RD New); gereprojecteerd naar "
              "WGS84. Download opnieuw met `download_bronnen.py --met-geometrie` voor "
              "bestanden die direct WGS84 zijn.")
    else:
        if buurten.crs is None:
            buurten = buurten.set_crs(epsg=4326)
        buurten = buurten.to_crs(epsg=4326)
    if "water" in buurten.columns:
        buurten = buurten[buurten["water"] == "NEE"].copy()

    cache: dict[str, tuple[float, float]] = {}
    unieke = net[pc6_kolom].dropna().unique()
    punten = []
    for i, pc6 in enumerate(unieke):
        cc = _pc6_centroide(pc6, cache)
        if cc:
            punten.append({"PC6": pc6, "geometry": Point(cc)})
        if pauze:
            time.sleep(pauze)
    if not punten:
        raise RuntimeError("Geen enkele PC6-centroide opgehaald — controleer netverbinding.")

    pts = gpd.GeoDataFrame(punten, crs="EPSG:4326")
    join = gpd.sjoin(pts, buurten[["buurtcode", "geometry"]], how="left", predicate="within")
    pc6_naar_buurt = join[["PC6", "buurtcode"]].drop_duplicates("PC6")

    out = net.merge(pc6_naar_buurt, left_on=pc6_kolom, right_on="PC6", how="left")
    return out


# --------------------------------------------------------------------------- #
# Route 3: CBS pc6hnr-crosswalk (indien beschikbaar)
# --------------------------------------------------------------------------- #
def koppel_pc6_via_crosswalk(
    net: pd.DataFrame,
    crosswalk_pad: str | Path,
    pc6_kolom: str = "PC6",
) -> pd.DataFrame:
    """Koppel via een CBS pc6hnr-koppeltabel (kolommen PC6 + Buurtcode<jaar>).

    Detecteert automatisch de buurtcode-kolom (bijv. 'Buurtcode2024').
    """
    cw = pd.read_csv(crosswalk_pad, dtype=str)
    pc6_col = next((c for c in cw.columns if c.upper() == "PC6"), None)
    buurt_col = next((c for c in cw.columns if c.lower().startswith("buurtcode")), None)
    if not pc6_col or not buurt_col:
        raise ValueError(f"Crosswalk mist PC6- of Buurtcode-kolom. Gevonden: {list(cw.columns)}")
    cw = cw[[pc6_col, buurt_col]].drop_duplicates(pc6_col)
    cw.columns = ["PC6", "buurtcode"]
    return net.merge(cw, left_on=pc6_kolom, right_on="PC6", how="left")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Koppel netbeheer-PC6 aan CBS-buurten.")
    p.add_argument("--liander", required=True, help="Pad naar Liander-TSV")
    p.add_argument("--pdok", help="Pad naar PDOK-buurt GeoJSON (attributen of geometrie)")
    p.add_argument("--crosswalk", help="Pad naar CBS pc6hnr-crosswalk CSV (route crosswalk)")
    p.add_argument("--route", choices=["pc4", "ruimtelijk", "crosswalk"], default="pc4")
    p.add_argument("--productsoort", choices=["GAS", "ELK"], default="GAS")
    p.add_argument("--uit", default="data/gekoppeld.csv", help="Pad voor de uitvoer-CSV")
    args = p.parse_args(argv)

    net = laad_liander(args.liander, productsoort=args.productsoort)
    print(f"Geladen: {len(net)} {args.productsoort}-rijen, {net['PC6'].nunique()} unieke PC6.")

    if args.route == "pc4":
        if not args.pdok:
            p.error("route pc4 vereist --pdok")
        res = koppel_pc6_via_pc4(net, args.pdok)
    elif args.route == "ruimtelijk":
        if not args.pdok:
            p.error("route ruimtelijk vereist --pdok (mét geometrie)")
        res = koppel_pc6_ruimtelijk(net, args.pdok)
    else:
        if not args.crosswalk:
            p.error("route crosswalk vereist --crosswalk")
        res = koppel_pc6_via_crosswalk(net, args.crosswalk)

    Path(args.uit).parent.mkdir(parents=True, exist_ok=True)
    res.to_csv(args.uit, index=False)
    print(f"Geschreven: {args.uit} ({len(res)} rijen, {len(res.columns)} kolommen).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
