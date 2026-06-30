---
name: wonen-energie-alternatieve-bronnen
description: Gebruik deze skill voor journalistiek onderzoek naar wonen en energie met open overheidsdata buiten CBS StatLine om. Inzetbaar als StatLine niet bereikbaar is of als aanvulling daarop. Dekt energieverbruik (gas en elektriciteit), zonnepanelen, aardgasvrije woningen, energielabels, woningwaarde en koopprijzen per buurt, wijk, gemeente en postcode, met geografische koppeling tussen bronnen via buurtcode en PC6.
---

## Doel

Deze skill maakt journalistiek onderzoek naar wonen en energietransitie mogelijk zonder CBS StatLine. Alle bronnen zijn open overheidsdata en direct opvraagbaar via de scripts in `scripts/`. Download eerst de data lokaal — dan werkt de analyse ook als een API tijdens de dag uitvalt.

Je kraakt een verhaal, je bouwt geen dashboard. Dat betekent: een scherpe bevinding over een buurt, wijk of gemeente, onderbouwd met data, eerlijk over onzekerheid. De houding is toetsen, niet bewijzen — zoek ook naar wat tegen je hypothese pleit.

## Wanneer gebruik je deze skill

- StatLine ligt plat en je hebt toch cijfers over wonen of energie nodig.
- Je wilt netbeheerdata (verbruik per postcode) koppelen aan CBS-kerncijfers per buurt.
- Je wilt energieverbruik, zonnepanelen, energielabels of woningwaarde vergelijken tussen buurten of gemeenten.
- Je wilt een tweede, onafhankelijke bron naast StatLine om een bevinding te controleren.

## Werkomgeving

De skill is bronagnostisch en draait in elke agent (kilo in VS Code, Claude Code, of een kale terminal). De scripts hebben alleen pandas, matplotlib en requests nodig; de ruimtelijke koppeling vraagt daarnaast geopandas. Zie `requirements.txt` en `README.md`.

```bash
pip install -r requirements.txt          # of: uv pip install -r requirements.txt
python scripts/download_bronnen.py --out data
```

## Geografische ruggengraat

De **PDOK CBS wijk- en buurtkaart** (`service.pdok.nl/cbs/wijkenbuurten/{jaar}/wfs/v1_0`) is het startpunt voor elke analyse. Per buurt bevat die de kerncijfers (woningvoorraad, WOZ-waarde, koop/huur, sociale huur, gasverbruik, elektriciteit, zonnestroom) plus de koppelsleutels `buurtcode` (BU########), `wijkcode` (WK######), `gemeentecode` (GM####).

Netbeheerdata zit op PC6-niveau. Breng die naar buurtniveau met `scripts/pc6_naar_buurt.py`. Andere bronnen koppel je direct op `buurtcode`.

**Kies de juiste jaargang — dit is cruciaal:**

| Wil je... | Gebruik PDOK-jaar | Reden |
|-----------|-------------------|-------|
| Gasverbruik totaal én per woningtype (huur/koop) | **2023** | Gas per woningtype is alleen in 2023 gevuld |
| Zonnepanelen, aardgasvrije woningen, stadsverwarming | **2024** | Deze velden bestaan alleen vanaf 2024 |
| Elektriciteit per buurt | 2024 (`gemiddeldeElektriciteitslevering`) | `gemiddeldElektriciteitsverbruikTotaal` is leeg |

Gebruik altijd dezelfde jaargang voor alle bronnen die je koppelt. Zie `references/kolomnamen.md` voor de volledige jaarmatrix.

## Werkwijze

1. **Hypothese** — formuleer een concrete onderzoeksvraag. Bijvoorbeeld: "Verbruiken bewoners van sociale-huurbuurten meer of minder gas dan koopbuurten, en verandert dat na correctie voor woningtype?"
2. **Data ophalen** — `python scripts/download_bronnen.py --out data --pdok-jaar 2023` (en `--pdok-jaar 2024` voor zon). Daarna werk je offline.
3. **Koppelen** — netbeheerdata aan buurt via `scripts/pc6_naar_buurt.py`; PDOK-bronnen direct op `buurtcode`.
4. **Toetsen** — bereken het patroon, deel in klassen of kwartielen, zoek uitschieters.
5. **Visualiseren** — `scripts/maak_top15.py` maakt de top-15 tabel en het staafdiagram met referentielijn voor het landelijk gemiddelde.
6. **Verifiëren** — controleer of uitschieters op een logische plek liggen, vermeld peildatum en dekking, en zoek tegenbewijs. Laat elke claim die in een demo komt verifiëren bij een CBS-expert.

## Output-contract

Elke analyse levert op:

- Een tabel met de top-15 buurten, wijken of gemeenten met de relevante kolommen.
- Een horizontaal staafdiagram met een referentielijn voor het landelijk gemiddelde.
- Een samenvatting van 3 tot 5 zinnen met de hoofdbevinding.
- Expliciete verificatiecriteria: verwacht aantal eenheden, peildatum, en bekende uitschieters op een logische plek.

### Vormgeving (huisstijl)

De output volgt het workshop-designsysteem: vlak, data-first, zinc-neutralen met één groen accent (`#00C853`) als signaalkleur. `scripts/maak_top15.py` heeft dit ingebouwd, dus je krijgt het automatisch.

- **Staafdiagram**: horizontale balken (hoogste bovenaan) in zinc-grijs `#71717a`, neutrale gestreepte referentielijn voor het landelijk gemiddelde, lichte gridlijnen (`#e4e4e7`), witte achtergrond, geen kaders. Getallen in monospace, Nederlandse notatie (`2.740`).
- **Verplichte elementen**: een titel die de *bevinding* benoemt (niet alleen de data), een ondertitel met bron en peildatum, de steekproefgrootte (`n = …`) en een bronvermelding. Reserveer het groene accent voor één signaal per figuur; gebruik geen extra kleuren.
- **Tabel**: maximaal ~6 kolommen, eenheden in de kop, getallen rechts uitgelijnd in Nederlandse notatie.
- **Weboutput (HTML/dashboard)**: gebruik het workshop-`design`-systeem (Inter + JetBrains Mono, de CSS-tokens, geen Bootstrap/Tailwind, geen ad-hoc hex). Roep de `design`-skill aan of laat `data-viz-journalism` de figuur maken.

```python
maak_top15(b, "gemiddeldAardgasverbruik", "buurtnaam",
           titel="Villabuurten in 't Gooi en Wassenaar stoken het meeste gas",   # bevinding, geen kale beschrijving
           subtitel="PDOK CBS-buurtkaart 2023 · peildatum 1-1-2023",
           eenheid="m3/jaar",
           bron="Bron: CBS/PDOK wijk- en buurtkaart 2023 (open data, CC0).",
           output_pad="data/top15_gas.png")
```

## Referenties

| Bestand | Inhoud |
|---------|--------|
| `references/bronnen.md` | Alle bronnen met URL, formaat, toegang en licentie — live geverifieerd |
| `references/kolomnamen.md` | Exacte kolomnamen per bron en de jaarmatrix (welke kolom in welk jaar gevuld is) |
| `references/recepten.md` | Vijf kant-en-klare koppelrecepten; recept 1 en 4 zijn end-to-end op echte data gedraaid |
| `references/valkuilen.md` | De veertien meestgemaakte fouten bij deze bronnen |
| `references/geo-koppeling.md` | De drie routes van PC6 naar buurt |

## Scripts

| Script | Functie |
|--------|---------|
| `scripts/download_bronnen.py` | Download netbeheer-TSV's en de PDOK-buurtkaart (met of zonder geometrie) naar `data/`, met logging |
| `scripts/pc6_naar_buurt.py` | Koppel PC6-netbeheerdata aan buurten (PC4-benadering, ruimtelijk, of CBS-crosswalk); bevat ook `laad_liander()` |
| `scripts/maak_top15.py` | Maak top-15 tabel en horizontaal staafdiagram met landelijke referentielijn uit een gekoppelde tabel |
