# Kolomnamen

Geverifieerd op echte, live gedownloade bestanden op 2026-06-30. De getallen achter "gevuld" komen uit een steekproef van 400 buurten en geven de richting aan — niet elke kolom is overal gevuld.

---

## Liander kleinverbruikdata (netbeheer-TSV)

Bestand: `verbruiksdata-kv-2025in.csv` → opgeslagen als `data/liander_2025.tsv` (268.857 regels).
Scheidingsteken: **tab**. Bestandsextensie is `.csv`, maar het is TSV.
Bijzonderheid: **elke regel staat tussen buitenste aanhalingstekens**.
Encoding: UTF-8.

| Kolomnaam | Type | Beschrijving |
|-----------|------|--------------|
| `AANSLUITINGEN_AANTAL` | int | Aantal aansluitingen in dit gebied. Altijd ≥ 10 (anonimiseringsdrempel). |
| `POSTCODE` | str | Begin-postcode van het aggregatiegebied (bijv. `1011AA`) |
| `POSTCODE_EIND` | str | Eind-postcode als meerdere PC6's zijn samengevoegd; gelijk aan `POSTCODE` bij één PC6 |
| `POSTCODE_AANTAL` | int | Aantal PC6-codes in het gebied |
| `PRODUCTSOORT` | str | `ELK` = elektriciteit, `GAS` = gas |
| `TYPE_AANSLUITING_MEEST_VOORKOMEND` | str | Meest voorkomend aansluitingstype (bijv. `1x25`, `3x25` voor ELK; `G4`, `G6` voor GAS) |
| `TOT_E` | int | Totaalverbruik in het gebied (kWh voor ELK, m³ voor GAS) |
| `SJA GEMIDDELD` | float | Gemiddeld standaardjaarverbruik per aansluiting (kWh of m³, temperatuurgecorrigeerd). **Spatie in de kolomnaam.** |

**Leeswijze** (de buitenste quotes breken `pandas.read_csv` met `sep='\t'`):
```python
import pandas as pd, io
with open('data/liander_2025.tsv', encoding='utf-8') as f:
    schoon = '\n'.join(line.strip().strip('"') for line in f if line.strip())
df = pd.read_csv(io.StringIO(schoon), sep='\t', dtype={'POSTCODE': str, 'POSTCODE_EIND': str})
df = df.rename(columns={'SJA GEMIDDELD': 'SJA_GEMIDDELD'})
gas = df[df['PRODUCTSOORT'] == 'GAS'].copy()
```
`scripts/pc6_naar_buurt.py` bevat dit als `laad_liander(pad, productsoort='GAS')`.

---

## PDOK wijk- en buurtkaart — buurten (WFS GeoJSON)

Endpoint: `https://service.pdok.nl/cbs/wijkenbuurten/{jaar}/wfs/v1_0`, laag `wijkenbuurten:buurten`. Circa 242 attributen per buurt.

### Sleutel- en filterkolommen

| Kolomnaam | Type | Beschrijving |
|-----------|------|--------------|
| `buurtcode` | str | BU########, bijv. `BU03630000`. Primaire koppelsleutel. |
| `buurtnaam` | str | Naam van de buurt |
| `wijkcode` | str | WK######, bijv. `WK036300` |
| `gemeentecode` | str | GM####, bijv. `GM0363` (Amsterdam) |
| `gemeentenaam` | str | Naam van de gemeente |
| `water` | str | **`NEE`** = land, `JA` = water, `B` = deels water. **Filter op `water == 'NEE'`** voor bewoonde buurten. (Let op: de waarde is `'NEE'`, niet `'N'`.) |
| `meestVoorkomendePostcode` | int | Meest voorkomende **4-cijferige** postcode (geen PC6) |

**Sentinelwaarden**: `-99997` en `-99998` (soms `-99995`) betekenen "niet beschikbaar/geheim", voor zowel int als float. Filter deze altijd weg vóór berekeningen.

### De jaarmatrix — welke kolom in welk jaar gevuld is

Dit is het belangrijkste punt van deze skill. Dezelfde kolomnaam kan in het ene jaar gevuld en in het andere jaar leeg (`-99997`) zijn. Live vastgesteld (gevuld van 400):

| Kolomnaam | Eenheid | 2023 | 2024 | Opmerking |
|-----------|---------|:----:|:----:|-----------|
| `gemiddeldAardgasverbruik` | m³/jaar | ✅ 235 | ✅ 234 | **De gaskolom.** Gebruik deze, in beide jaren. |
| `gemiddeldGasverbruikTotaal` | m³/jaar | ❌ 0 | ❌ 0 | Bestaat in het schema maar is **altijd leeg**. Niet gebruiken. |
| `gemiddeldGasverbruikHuurwoning` | m³/jaar | ✅ 212 | ❌ 0 | Gas per woningtype alleen in **2023** |
| `gemiddeldGasverbruikkoopwoning` | m³/jaar | ✅ 226 | ❌ 0 | Let op kleine `k` in `koopwoning` |
| `gemiddeldGasverbruikAppartement` | m³/jaar | ✅ | ❌ 0 | idem (2023) |
| `gemiddeldGasverbruikTussenwoning` | m³/jaar | ✅ | ❌ 0 | idem (2023) |
| `gemiddeldGasverbruikHoekwoning` | m³/jaar | ✅ | ❌ 0 | idem (2023) |
| `gemiddeldGasverbruik2Onder1KapWoning` | m³/jaar | ✅ | ❌ 0 | idem (2023) |
| `gemiddeldGasverbruikVrijstaandeWoning` | m³/jaar | ✅ | ❌ 0 | idem (2023) |
| `gemiddeldElektriciteitsverbruikTotaal` | kWh/jaar | ✅ | ❌ 0 | In 2024 leeg |
| `gemiddeldeElektriciteitslevering` | kWh/jaar | ✅ | ✅ 240 | **Gebruik deze voor elektriciteit in 2024** |
| `percentageWoningenMetZonnestroom` | % | ❌ bestaat niet | ✅ 196 | Zonnepanelen alleen in **2024** |
| `percentageAardgasvrijeWoningen` | % | ❌ bestaat niet | ✅ 196 | Alleen in **2024** |
| `percentageAardgaswoningen` | % | ❌ bestaat niet | ✅ 196 | Alleen in **2024** |
| `percentageWoningenMetStadsverwarming` | % | ❌ bestaat niet | ✅ 89 | Alleen in **2024** |

> Vuistregel: **2023 voor gas (incl. woningtype)**, **2024 voor zon, aardgasvrij en stadsverwarming**.

### Woning- en welvaartskolommen (gevuld in 2023 én 2024)

| Kolomnaam | Eenheid | Beschrijving |
|-----------|---------|--------------|
| `woningvoorraad` | aantal | Totaal aantal woningen |
| `gemiddeldeWoningwaarde` | × €1.000 | Gemiddelde WOZ-waarde per woning |
| `percentageEengezinswoning` | % | Aandeel eengezinswoningen |
| `percentageMeergezinswoning` | % | Aandeel appartementen |
| `percentageKoopwoningen` | % | Aandeel koopwoningen |
| `percentageHuurwoningen` | % | Aandeel huurwoningen |
| `percHuurwoningenInBezitWoningcorporaties` | % | Aandeel sociale huur (corporaties) |
| `percHuurwoningenInBezitOverigeVerhuurders` | % | Aandeel particuliere huur |
| `aantalInwoners` | aantal | Inwoners |
| `aantalHuishoudens` | aantal | Huishoudens |
| `mediaanVermogenVanParticuliereHuish` | × €1.000 | Mediaan vermogen particuliere huishoudens |
| `omgevingsadressendichtheid` | adr/km² | Stedelijkheid (hoger = stedelijker) |

### Veilige WFS-query

```python
from urllib.request import urlopen
from urllib.parse import urlencode
import json

base = "https://service.pdok.nl/cbs/wijkenbuurten/2023/wfs/v1_0"
params = {
    "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
    "TYPENAMES": "wijkenbuurten:buurten", "OUTPUTFORMAT": "application/json",
    "COUNT": "1000", "STARTINDEX": "0",
    "PROPERTYNAME": "buurtcode,buurtnaam,gemeentenaam,water,"
                    "percHuurwoningenInBezitWoningcorporaties,gemiddeldAardgasverbruik,"
                    "gemiddeldGasverbruikHuurwoning,gemiddeldGasverbruikkoopwoning,"
                    "gemiddeldeWoningwaarde,percentageEengezinswoning",
}
feats = json.loads(urlopen(f"{base}?{urlencode(params)}").read())["features"]
# Herhaal met STARTINDEX 1000, 2000, ... — de WFS levert max 1000 per request.
```
`scripts/download_bronnen.py` doet de paginering, geometrie-strip en veldfiltering automatisch.

---

## Hoe controleer je de kolommen zelf?

```bash
# Welke velden bestaan in deze jaargang?
curl -s "https://service.pdok.nl/cbs/wijkenbuurten/2024/wfs/v1_0?SERVICE=WFS&VERSION=2.0.0&REQUEST=DescribeFeatureType&TYPENAMES=wijkenbuurten:buurten" \
  | grep -oE 'name="[a-zA-Z0-9]+"'
```
Of `head -1 data/liander_2025.tsv` voor de netbeheer-header. Vertrouw nooit een kolomnaam zonder hem tegen een echt bestand te controleren.
