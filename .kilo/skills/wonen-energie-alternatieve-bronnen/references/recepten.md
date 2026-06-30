# Recepten

Vijf kant-en-klare koppelpatronen voor de meest gevraagde wonen-energie-verhaallijnen. Recept 1 en 4 zijn op 2026-06-30 **end-to-end op echte data gedraaid**; de getoonde tabellen zijn de werkelijke uitkomst. Lees `valkuilen.md` voordat je publiceert.

Alle recepten gaan uit van data in `data/`, opgehaald met:
```bash
python scripts/download_bronnen.py --out data --pdok-jaar 2023   # gas
python scripts/download_bronnen.py --out data --geen-liander --pdok-jaar 2024   # zon
```

---

## Recept 1 — Energiearmoede-indicatie: gas en sociale huur ✅ getest

**Vraag**: Verbruiken bewoners van sociale-huurbuurten meer of minder gas dan koopbuurten, en wat blijft er over na correctie voor woningtype?

**Bronnen**: PDOK-buurtkaart **2023** (heeft gas totaal én per woningtype). Geen netbeheerdata nodig — PDOK is NL-breed.

**Code** (draait zoals hieronder, met `scripts/` op het pad):
```python
import sys; sys.path.insert(0, "scripts")
import pandas as pd
from pc6_naar_buurt import laad_pdok_attributen, SENTINELS
from maak_top15 import maak_top15

b = laad_pdok_attributen("data/pdok_buurten_2023.geojson")   # filtert water == 'NEE'
for c in ["percHuurwoningenInBezitWoningcorporaties", "gemiddeldAardgasverbruik",
          "gemiddeldGasverbruikHuurwoning", "gemiddeldGasverbruikkoopwoning",
          "gemiddeldeWoningwaarde", "percentageEengezinswoning"]:
    b[c] = pd.to_numeric(b[c], errors="coerce")
    b.loc[b[c].isin(SENTINELS), c] = float("nan")
b = b.dropna(subset=["percHuurwoningenInBezitWoningcorporaties", "gemiddeldAardgasverbruik"])

# Vaste klassen: veel buurten hebben 0% sociale huur, dus pd.qcut faalt (zie valkuilen 11).
b["klasse"] = pd.cut(b["percHuurwoningenInBezitWoningcorporaties"],
                     bins=[-0.1, 15, 40, 70, 100.1],
                     labels=["0-15% soc.huur", "15-40%", "40-70%", ">70% soc.huur"])
res = b.groupby("klasse", observed=True).agg(
    gas=("gemiddeldAardgasverbruik", "mean"),
    gas_huur=("gemiddeldGasverbruikHuurwoning", "mean"),
    gas_koop=("gemiddeldGasverbruikkoopwoning", "mean"),
    pct_egw=("percentageEengezinswoning", "mean"),
    woz=("gemiddeldeWoningwaarde", "mean"),
    n=("buurtcode", "count")).round(0)
print(res)

maak_top15(b, "gemiddeldAardgasverbruik", "buurtnaam",
           titel="Villabuurten in 't Gooi en Wassenaar stoken het meeste gas",
           subtitel="PDOK CBS-buurtkaart 2023 · peildatum 1-1-2023 · gemiddeld aardgasverbruik per woning",
           eenheid="m3/jaar",
           bron="Bron: CBS/PDOK wijk- en buurtkaart 2023 (open data, CC0).",
           output_pad="data/top15_gas.png")
```

**Werkelijke uitkomst** (PDOK 2023, n = 12.724 buurten, landelijk gemiddelde **990 m³/jaar**):

| Klasse | Gas m³ | Gas huur | Gas koop | % egw | WOZ €k | n |
|--------|-------:|---------:|---------:|------:|-------:|----:|
| 0–15% soc.huur | **1.148** | 1.060 | 1.177 | 85 | 485 | 6.955 |
| 15–40% | **843** | 700 | 929 | 73 | 357 | 3.920 |
| 40–70% | **726** | 655 | 840 | 54 | 297 | 1.481 |
| >70% soc.huur | **636** | 617 | 782 | 36 | 246 | 368 |

**Bevinding**: Buurten met meer sociale huur verbruiken minder gas — maar dat komt grotendeels doordat ze meer appartementen hebben (% eengezinswoning daalt van 85 naar 36). Het effect blijft ook binnen woningtype zichtbaar: een koopwoning in een sociale-huurbuurt (782 m³) verbruikt minder dan een koopwoning in een koopbuurt (1.177 m³). Dat wijst op woningkenmerken (bouwjaar, isolatie, grootte), niet op de eigendomsvorm zelf.

**Top 15 hoogste gasverbruik** — uitsluitend villabuurten met ~0% sociale huur en ~100% eengezinswoningen: De Kieviet (Wassenaar, 2.740 m³), Rijksweg-Zuid (Laren), Crailo (Blaricum), en meer buurten in 't Gooi en Wassenaar. Dit is precies de logische plek voor uitschieters: grote vrijstaande woningen in welvarende gemeenten. De werkelijke uitvoer is meegeleverd als voorbeeld: diagram `references/voorbeeld-output/top15_gas.png`, tabellen `references/voorbeeld-output/recept1_top15.csv` en `recept1_kwartielen.csv`. (Bij eigen draaien schrijven de scripts naar `data/`.)

**Verificatiecriteria**: ~12.700 buurten verwacht; peildatum PDOK 2023; uitschieters horen vrijstaande-woningbuurten te zijn. Komt een sociale-huurbuurt onverwacht hoog uit, controleer dan het woningtype en de woningvoorraad (kleine buurten zijn volatiel).

---

## Recept 2 — Daling gasverbruik per buurt over meerdere jaren

**Vraag**: Welke buurten tonen de sterkste daling in gasverbruik per woning tussen twee peildata?

**Bronnen**: netbeheerdata van twee jaargangen (bijv. Liander 2023 en 2025), gekoppeld aan buurt; of twee PDOK-jaargangen.

```python
import sys; sys.path.insert(0, "scripts")
from pc6_naar_buurt import laad_liander, koppel_pc6_via_pc4
import pandas as pd

g22 = koppel_pc6_via_pc4(laad_liander("data/liander_2023.tsv", "GAS"),
                         "data/pdok_buurten_2023.geojson")[["buurtcode", "SJA_GEMIDDELD_pc4_gem"]]
g25 = koppel_pc6_via_pc4(laad_liander("data/liander_2025.tsv", "GAS"),
                         "data/pdok_buurten_2024.geojson")[["buurtcode", "SJA_GEMIDDELD_pc4_gem"]]
trend = g22.merge(g25, on="buurtcode", suffixes=("_2023", "_2025")).dropna()
trend["pct_daling"] = (trend["SJA_GEMIDDELD_pc4_gem_2023"] - trend["SJA_GEMIDDELD_pc4_gem_2025"]) \
                      / trend["SJA_GEMIDDELD_pc4_gem_2023"] * 100
print(trend.sort_values("pct_daling", ascending=False).head(20))
```

**Verificatiecriteria**: landelijke daling 2022→2024 ligt naar verwachting rond 5–15% (energiecrisis + transitie). Daling >30%: controleer of de buurt niet van karakter veranderde (nieuwbouw/sloop). Standaardjaarverbruik is temperatuurgecorrigeerd en mag je over jaren vergelijken — zie `valkuilen.md` punt 3 voor de breuk bij elektriciteit.

---

## Recept 3 — Energielabel versus eigendom

**Vraag**: Hebben huurwoningen in een buurt slechtere energielabels dan koopwoningen?

**Bronnen**: EP-Online bulk (API-key) + PDOK-buurtkaart (koop/huur %).

```python
import pandas as pd
labels = pd.read_csv("data/ep_online_labels.csv", dtype={"postcode": str})  # check de header!
labels["energieklasse"] = labels["energieklasse"].str.upper().str.strip()
labels["label_ef_g"] = labels["energieklasse"].isin(["E", "F", "G"])
pc6 = labels.groupby("postcode").agg(pct_slecht=("label_ef_g", "mean"),
                                     n_labels=("energieklasse", "count")).reset_index()
# Koppel postcode -> buurt (scripts/pc6_naar_buurt.py), aggregeer naar buurt, join PDOK koop/huur.
```

**Verificatiecriteria**: vermeld de **dekking** (`n_labels` / `woningvoorraad`). Energielabels kennen selectiebias — neem een buurt alleen mee bij voldoende dekking (bijv. > 30%). Zeg "van de woningen met een geregistreerd label", niet "van alle woningen". Zie `valkuilen.md` punt 4.

---

## Recept 4 — Zonnepanelen en welvaart ✅ getest

**Vraag**: Zijn zonnepanelen geconcentreerd in welvarendere buurten?

**Bronnen**: PDOK-buurtkaart **2024** (zonnestroom bestaat alleen in 2024). Geen extra bron nodig.

```python
import sys; sys.path.insert(0, "scripts")
import pandas as pd
from pc6_naar_buurt import laad_pdok_attributen, SENTINELS

b = laad_pdok_attributen("data/pdok_buurten_2024.geojson")
for c in ["percentageWoningenMetZonnestroom", "gemiddeldeWoningwaarde", "percentageEengezinswoning"]:
    b[c] = pd.to_numeric(b[c], errors="coerce")
    b.loc[b[c].isin(SENTINELS), c] = float("nan")
b = b.dropna(subset=["percentageWoningenMetZonnestroom", "gemiddeldeWoningwaarde"])
b["woz_klasse"] = pd.qcut(b["gemiddeldeWoningwaarde"], 4,
                          labels=["Q1 laagste WOZ", "Q2", "Q3", "Q4 hoogste WOZ"])
print(b.groupby("woz_klasse", observed=True).agg(
    zon=("percentageWoningenMetZonnestroom", "mean"),
    woz=("gemiddeldeWoningwaarde", "mean"),
    egw=("percentageEengezinswoning", "mean"),
    n=("buurtcode", "count")).round(1))
```

**Werkelijke uitkomst** (PDOK 2024, n = 10.093 buurten, landelijk gemiddelde **41,7%** woningen met zonnestroom):

| WOZ-kwartiel | % zon | WOZ €k | % egw | n |
|--------------|------:|-------:|------:|----:|
| Q1 laagste WOZ | 33,1 | 251 | 61,5 | 2.544 |
| Q2 | 40,9 | 341 | 73,3 | 2.534 |
| Q3 | 46,2 | 424 | 77,8 | 2.509 |
| Q4 hoogste WOZ | 46,8 | 611 | 78,3 | 2.506 |

**Bevinding**: Zonnepanelen nemen toe met woningwaarde (33% → 47%), maar het verschil tussen Q3 en Q4 is klein. Een groot deel van het patroon loopt via woningtype: in lage-WOZ-buurten staan meer appartementen (61% eengezinswoning vs 78%), en appartementen hebben zelden eigen dak. Corrigeer voor woningtype of filter op eengezinswoningen voordat je een welvaartsclaim maakt.

**Verificatiecriteria**: hogere WOZ hoort meer zon te tonen. Uitschieters: nieuwbouwbuurten met zonneplicht of sociale-huurcomplexen met collectieve panelen.

---

## Recept 5 — Sociale huur versus woningwaarde per gemeente

**Vraag**: Hebben gemeenten met veel sociale huur een lager waardeniveau van de woningvoorraad?

**Bronnen**: PDOK **gemeenten**-laag (`--pdok-niveau gemeenten`).

```python
import sys; sys.path.insert(0, "scripts")
import pandas as pd
from pc6_naar_buurt import laad_pdok_attributen, SENTINELS

g = laad_pdok_attributen("data/pdok_gemeenten_2024.geojson")  # download met --pdok-niveau gemeenten
for c in ["gemiddeldeWoningwaarde", "percHuurwoningenInBezitWoningcorporaties"]:
    g[c] = pd.to_numeric(g[c], errors="coerce")
    g.loc[g[c].isin(SENTINELS), c] = float("nan")
g = g.dropna(subset=["gemiddeldeWoningwaarde", "percHuurwoningenInBezitWoningcorporaties"])
g["klasse"] = pd.qcut(g["percHuurwoningenInBezitWoningcorporaties"], 4,
                      labels=["Q1 weinig", "Q2", "Q3", "Q4 veel soc.huur"])
print(g.groupby("klasse", observed=True).agg(
    woz=("gemiddeldeWoningwaarde", "mean"), n=("gemeentecode", "count")).round(0))
```

**Beperking**: WOZ is een waardeniveau, geen prijsontwikkeling. Voor prijsontwikkeling over de tijd hoort de Prijsindex Bestaande Koopwoningen (Kadaster/CBS), niet de gemiddelde koopsom. Zie `valkuilen.md` punt 6.

**Verificatiecriteria**: ~340 gemeenten verwacht. Kleine gemeenten met weinig transacties hebben volatiele gemiddelden.
