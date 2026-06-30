# Geografische koppeling

Netbeheerdata zit op PC6-niveau; alle andere bronnen zitten op buurt-, wijk- of gemeenteniveau. Dit bestand legt uit hoe je PC6 naar buurt brengt.

---

## Het probleem

| Bron | Niveau | Sleutel |
|------|--------|---------|
| Netbeheerdata (Liander, Enexis, Stedin) | PC6 (`1011AA`) | `POSTCODE` |
| PDOK-buurtkaart + CBS-kerncijfers | buurt (BU########) | `buurtcode` |
| EP-Online energielabels | adres (BAG) → PC6 | postcode + huisnummer |

Er is geen altijd-beschikbare officiële PC6→buurt-crosswalk buiten CBS StatLine om. `scripts/pc6_naar_buurt.py` biedt daarom drie routes.

---

## Regiohiërarchie

```
Nederland
 └── Provincie (PV##)
      └── Gemeente (GM####)
           └── Wijk (WK######)
                └── Buurt (BU########)   ← de meeste analyses
                     ↑
                PC6 (1011AA)             ← netbeheerdata
```
Aggregeer van buurt omhoog door te groeperen op `wijkcode` of `gemeentecode`.

---

## Route 1 — PC4-benadering (`--route pc4`, alleen pandas)

Aggregeer netbeheerdata op de eerste 4 cijfers van de postcode en koppel aan het PDOK-veld `meestVoorkomendePostcode`.

- **Voordeel**: snel, geen geo-bibliotheken, werkt altijd.
- **Nadeel**: grof. Meerdere buurten delen dezelfde PC4; de dekking is beperkt (Liander 2025 → ~37% van de buurten). Gebruik voor oriëntatie, niet voor publicatie.

```python
from pc6_naar_buurt import laad_liander, koppel_pc6_via_pc4
gas = laad_liander("data/liander_2025.tsv", "GAS")
gekoppeld = koppel_pc6_via_pc4(gas, "data/pdok_buurten_2023.geojson")
# kolom SJA_GEMIDDELD_pc4_gem = PC4-gemiddelde per buurt
```

---

## Route 2 — Ruimtelijke koppeling (`--route ruimtelijk`, geopandas)

De nauwkeurige route, zonder externe crosswalk: zoek de centroïde van elke PC6 op en bepaal met een point-in-polygon-join in welke buurt die valt.

**Stappen**:
1. Download PDOK-buurtpolygonen **mét geometrie**: `python scripts/download_bronnen.py --pdok-jaar 2024 --met-geometrie`.
2. Zoek per unieke PC6 de centroïde via de PDOK Locatieserver (met cache).
3. Point-in-polygon-join met geopandas.

**PDOK Locatieserver** (geverifieerd, HTTP 200):
```
https://api.pdok.nl/bzk/locatieserver/search/v3_1/free?q={pc6}&rows=1&fl=centroide_ll&fq=type:postcode
→ "centroide_ll": "POINT(4.90185421 52.37289416)"   # lon lat, WGS84
```

- **Voordeel**: nauwkeurig, werkt ook als StatLine en andere crosswalks uitvallen.
- **Nadeel**: trager (één Locatieserver-call per unieke PC6 — de cache beperkt dat), en vereist `geopandas` + `shapely` (`uv pip install geopandas shapely`).

```python
from pc6_naar_buurt import laad_liander, koppel_pc6_ruimtelijk
gas = laad_liander("data/liander_2025.tsv", "GAS")
gekoppeld = koppel_pc6_ruimtelijk(gas, "data/pdok_buurten_2024_geo.geojson")
# voegt kolom 'buurtcode' toe per PC6
```

---

## Route 3 — CBS pc6hnr-crosswalk (`--route crosswalk`, indien beschikbaar)

CBS publiceert jaarlijks een koppeltabel PC6 → buurtcode (`pc6hnr{jaar}01_gwb`). Normaal via StatLine of `download.cbs.nl`. Was op 2026-06-30 niet via een publieke directe URL beschikbaar, maar als je het bestand op een gedeelde schijf hebt, is dit de snelste en nauwkeurigste route.

Verwachte kolommen: `PC6`, `Huisnummer`, `Buurtcode{jaar}`, `Wijkcode{jaar}`, `Gemeentecode{jaar}`. Het script detecteert de buurtcode-kolom automatisch.

```python
from pc6_naar_buurt import laad_liander, koppel_pc6_via_crosswalk
gas = laad_liander("data/liander_2025.tsv", "GAS")
gekoppeld = koppel_pc6_via_crosswalk(gas, "data/pc6hnr20240101_gwb.csv")
```

---

## Welke route kies je?

| Situatie | Route |
|----------|-------|
| Snel oriënteren, geen geo-libs | PC4 |
| Publicatie, geopandas beschikbaar | Ruimtelijk |
| CBS pc6hnr-bestand op schijf | Crosswalk |

Vermeld in je analyse welke route je gebruikte en, bij PC4, dat het een benadering is.
