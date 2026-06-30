#!/usr/bin/env python3
"""Maak een top-15 tabel en horizontaal staafdiagram uit een gekoppelde tabel.

Hulpscript voor de output van deze skill: gegeven een tabel met een waarde- en een
labelkolom, levert het de 15 hoogste (of laagste) eenheden plus een staafdiagram met
een referentielijn voor het landelijk gemiddelde — het standaard output-contract.

Gebruik als module:
    from maak_top15 import maak_top15
    tabel = maak_top15(df, waarde_kolom="gemiddeldAardgasverbruik", label_kolom="buurtnaam",
                       titel="Top 15 buurten: hoogste gasverbruik (PDOK 2023)",
                       eenheid="m3/jaar", output_pad="data/top15_gas.png")

Gebruik als script:
    python maak_top15.py --csv data/gekoppeld.csv --waarde gemiddeldAardgasverbruik \
        --label buurtnaam --titel "Top 15 gasverbruik" --eenheid "m3/jaar" \
        --out data/top15_gas.png
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # geen scherm nodig — schrijft direct naar bestand
import matplotlib.pyplot as plt
import pandas as pd

SENTINELS = (-99997, -99998, -99995, -99997.0, -99998.0, -99995.0)

# Huisstijl: tokens uit het workshop-designsysteem (zinc-neutralen, één groen accent,
# vlak, data-first). Zie de subsectie "Vormgeving" in SKILL.md → Output-contract.
# Geen willekeurige hex-waarden — uitsluitend deze tokens gebruiken.
STIJL = {
    "bg": "#fafafa",          # --bg
    "balk": "#71717a",        # zinc-500, neutrale serie (geen waardeoordeel)
    "balk_nadruk": "#52525b",  # zinc-600, lichte nadruk voor de hoogste balk
    "lijn": "#18181b",        # --fg, neutrale referentielijn
    "accent": "#00C853",      # signaalkleur — spaarzaam, één per figuur
    "tekst": "#18181b",       # --fg
    "subtiel": "#71717a",     # --fg-dim
    "grid": "#e4e4e7",        # --border
}


def _nl_getal(x: float) -> str:
    """Formatteer een getal in Nederlandse stijl: punt als duizendtalscheiding."""
    return f"{x:,.0f}".replace(",", ".")


def maak_top15(
    df: pd.DataFrame,
    waarde_kolom: str,
    label_kolom: str,
    titel: str,
    eenheid: str = "",
    landelijk_gemiddelde: float | None = None,
    n: int = 15,
    oplopend: bool = False,
    output_pad: str | Path | None = None,
    subtitel: str = "",
    bron: str = "Bron: CBS/PDOK wijk- en buurtkaart en netbeheerders (open data).",
) -> pd.DataFrame:
    """Bereken de top-n en teken het staafdiagram in de huisstijl van de skill.

    Volgt het output-contract: horizontale balken (hoogste bovenaan), een rode
    gestreepte referentielijn voor het landelijk gemiddelde, waardelabels aan de
    balken, een grijze ondertitel (bijv. bron + peildatum) en een bronvermelding
    linksonder. Getallen in Nederlandse notatie (punt als duizendtalscheiding).

    `landelijk_gemiddelde` standaard = gemiddelde over alle geldige rijen.
    `oplopend=True` geeft de laagste n. Retourneert de top-n als DataFrame.
    """
    werk = df[[label_kolom, waarde_kolom]].copy()
    werk[waarde_kolom] = pd.to_numeric(werk[waarde_kolom], errors="coerce")
    werk = werk[~werk[waarde_kolom].isin(SENTINELS)].dropna(subset=[waarde_kolom])
    if werk.empty:
        raise ValueError(f"Geen geldige waarden in kolom '{waarde_kolom}' na opschonen.")

    if landelijk_gemiddelde is None:
        landelijk_gemiddelde = float(werk[waarde_kolom].mean())

    top = werk.sort_values(waarde_kolom, ascending=oplopend).head(n)
    volgorde = top.iloc[::-1]  # hoogste bovenaan in de grafiek

    # Inter/JetBrains Mono zijn niet offline beschikbaar; val terug op DejaVu.
    # Mono voor getallen (waardelabels, assen), sans voor tekst — designregel.
    mono = {"fontfamily": "DejaVu Sans Mono"}
    fig, ax = plt.subplots(figsize=(10, 7))
    fig.patch.set_facecolor(STIJL["bg"])
    ax.set_facecolor(STIJL["bg"])

    posities = list(range(len(volgorde)))
    # Neutrale zinc-balken; alleen de hoogste krijgt lichte nadruk (geen extra accent).
    kleuren = [STIJL["balk"]] * len(volgorde)
    if kleuren:
        kleuren[-1 if not oplopend else 0] = STIJL["balk_nadruk"]
    balken = ax.barh(posities, volgorde[waarde_kolom], color=kleuren, zorder=3)
    ax.set_yticks(posities)
    ax.set_yticklabels(volgorde[label_kolom].astype(str), color=STIJL["tekst"])

    # Waardelabels (mono) aan het eind van elke balk.
    marge = volgorde[waarde_kolom].max() * 0.01
    for rect, waarde in zip(balken, volgorde[waarde_kolom]):
        ax.text(rect.get_width() + marge, rect.get_y() + rect.get_height() / 2,
                _nl_getal(waarde), va="center", ha="left",
                fontsize=9, color=STIJL["subtiel"], zorder=4, **mono)

    # Landelijke referentielijn — neutraal (geen waardeoordeel), niet het groene accent.
    ax.axvline(landelijk_gemiddelde, color=STIJL["lijn"], linestyle="--", linewidth=1.4,
               zorder=2,
               label=f"Landelijk gemiddelde: {_nl_getal(landelijk_gemiddelde)} {eenheid}".strip())

    ax.set_xlabel(f"{waarde_kolom} ({eenheid})" if eenheid else waarde_kolom,
                  color=STIJL["subtiel"])
    for lbl in ax.get_xticklabels():
        lbl.set_fontfamily("DejaVu Sans Mono")
        lbl.set_color(STIJL["subtiel"])
    # Titel: formuleer de bevinding, niet alleen de data (designregel).
    ax.set_title(titel, fontsize=15, fontweight="bold", color=STIJL["tekst"],
                 loc="left", pad=24 if subtitel else 12)
    if subtitel:
        ax.text(0.0, 1.02, subtitel, transform=ax.transAxes, fontsize=10,
                color=STIJL["subtiel"], ha="left", va="bottom")

    # Steekproefgrootte rechtsboven (designregel: altijd n vermelden).
    ax.text(1.0, 1.02, f"n = {_nl_getal(len(werk))}", transform=ax.transAxes,
            fontsize=10, color=STIJL["subtiel"], ha="right", va="bottom", **mono)

    ax.grid(axis="x", color=STIJL["grid"], linewidth=0.8, zorder=0)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(STIJL["grid"])
    ax.tick_params(length=0)
    ax.legend(loc="lower right", frameon=False)

    # Bronvermelding linksonder (designregel: altijd attributie).
    fig.text(0.01, 0.01, bron, fontsize=8, color=STIJL["subtiel"], ha="left")
    fig.tight_layout(rect=(0, 0.03, 1, 1))

    if output_pad:
        Path(output_pad).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_pad, dpi=120, facecolor="white")
        print(f"Diagram geschreven: {output_pad}")
    plt.close(fig)

    return top.reset_index(drop=True)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Top-15 tabel + staafdiagram uit een gekoppelde CSV.")
    p.add_argument("--csv", required=True, help="Invoer-CSV (gekoppelde tabel)")
    p.add_argument("--waarde", required=True, help="Naam van de waardekolom")
    p.add_argument("--label", required=True, help="Naam van de labelkolom (bijv. buurtnaam)")
    p.add_argument("--titel", default="Top 15", help="Titel van het diagram")
    p.add_argument("--subtitel", default="", help="Grijze ondertitel (bijv. bron + peildatum)")
    p.add_argument("--bron", default="Bron: CBS/PDOK wijk- en buurtkaart en netbeheerders (open data).",
                   help="Bronvermelding linksonder")
    p.add_argument("--eenheid", default="", help="Eenheid voor de as/legenda (bijv. 'm3/jaar')")
    p.add_argument("--n", type=int, default=15, help="Aantal eenheden (default 15)")
    p.add_argument("--oplopend", action="store_true", help="Toon de laagste i.p.v. hoogste")
    p.add_argument("--out", default="data/top15.png", help="Pad voor het PNG-diagram")
    p.add_argument("--uit-csv", help="Optioneel: schrijf de top-n ook als CSV")
    args = p.parse_args(argv)

    df = pd.read_csv(args.csv)
    top = maak_top15(df, args.waarde, args.label, args.titel, args.eenheid,
                     n=args.n, oplopend=args.oplopend, output_pad=args.out,
                     subtitel=args.subtitel, bron=args.bron)
    print(top.to_string(index=False))
    if args.uit_csv:
        top.to_csv(args.uit_csv, index=False)
        print(f"Top-{args.n} geschreven: {args.uit_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
