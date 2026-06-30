# Bronnen

Alle URL's live geverifieerd op 2026-06-30 (HTTP 200, tenzij anders vermeld). Controleer URL's bij gebruik — overheidsportals wijzigen regelmatig paden.

---

## 1. PDOK CBS wijk- en buurtkaart (ruggengraat)

**Wat**: Geometrie van alle buurten, wijken en gemeenten in Nederland, met CBS-kerncijfers als attributen: woningvoorraad, WOZ-waarde, eigendom (koop/huur/sociale huur), gasverbruik, elektriciteit, zonnestroom, aardgasvrije woningen en meer.

**Geografisch niveau**: buurt (BU########), wijk (WK######), gemeente (GM####).

**Formaat**: WFS (GeoJSON, GML), WMS. Geen directe GeoPackage-download; gebruik de WFS.

**Toegang**:
- WFS: `https://service.pdok.nl/cbs/wijkenbuurten/{jaar}/wfs/v1_0`
- Lagen: `wijkenbuurten:buurten`, `wijkenbuurten:wijken`, `wijkenbuurten:gemeenten`
- Beschikbare jaren: 2022, 2023, 2024 (alle HTTP 200 geverifieerd)
- GetCapabilities: `?SERVICE=WFS&REQUEST=GetCapabilities`
- DescribeFeatureType (kolomnamen per jaar): `?SERVICE=WFS&VERSION=2.0.0&REQUEST=DescribeFeatureType&TYPENAMES=wijkenbuurten:buurten`
- GetFeature (GeoJSON): `?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=wijkenbuurten:buurten&OUTPUTFORMAT=application/json&COUNT=1000&STARTINDEX=0`

**Belangrijke technische punten** (live vastgesteld):
- De WFS levert **maximaal 1000 features per request**, ongeacht `COUNT`. Pagineer met `STARTINDEX` (0, 1000, 2000, ...). Nederland heeft ~14.500 buurten.
- `PROPERTYNAME` beperkt de *attributen*, maar de WFS levert de **geometrie tóch** mee. Strip die na het downloaden als je alleen attributen nodig hebt (doet `download_bronnen.py` automatisch).
- De WFS weigert het hele verzoek (HTTP 400) als ook maar één `PROPERTYNAME` niet bestaat in die jaargang. Kolommen verschillen per jaar — `download_bronnen.py` filtert de gevraagde lijst eerst tegen `DescribeFeatureType`.

**Coördinatenstelsel**: GeoJSON-output is WGS84 (EPSG:4326); bronprojectie is EPSG:28992 (RD New).

**Updatefrequentie**: jaarlijks (nieuw jaarnummer in de URL).

**Licentie**: open data, CC0.

**Aandachtspunt**: gebruik altijd hetzelfde jaar voor alle gekoppelde bronnen. Buurtcodes en -grenzen wijzigen per jaar. Welke kolom in welk jaar gevuld is, staat in `kolomnamen.md`.

---

## 2. Kleinverbruikdata netbeheerders (energieverbruik per postcode)

**Wat**: Jaarlijkse gegevens van gas- en elektriciteitsverbruik per PC6, geanonimiseerd voor gebieden met minimaal 10 aansluitingen. Gas in m³, elektriciteit in kWh, als standaardjaarverbruik (temperatuurgecorrigeerd).

**Geografisch niveau**: PC6 (bijv. `1011AA`). Koppel aan buurt via `scripts/pc6_naar_buurt.py`.

**Formaat**: TSV (tab-gescheiden), met bestandsextensie `.csv`. Elke regel staat tussen buitenste aanhalingstekens. Zie `kolomnamen.md` voor de leeswijze.

**Peildatum**: 1 januari van het betreffende jaar.

**Licentie**: CC-BY 4.0.

### Liander (o.a. Noord-Holland, Flevoland, Friesland, Gelderland, deel Utrecht en Noord-Brabant)

- Open-data pagina: `https://www.liander.nl/over-ons/open-data`
- Directe download 2025 (peildatum 1-1-2025): `https://www.liander.nl/-/media/files/open-data/kleinverbruikdata/verbruiksdata-kv-2025in.csv`
- **Geverifieerd**: HTTP 200 op 2026-06-30. Bestand: 13,8 MB, 268.857 regels (excl. header). Bevat 121.577 GAS-rijen en de rest ELK.
- Oudere jaren via dezelfde pagina (deels ZIP).

### Enexis (o.a. Groningen, Drenthe, Overijssel, Limburg, Zeeland, deel Noord-Brabant)

- Open-data pagina: `https://www.enexis.nl/over-ons/open-data`
- **Toegang**: aanvraag via Partners in Energie (`https://www.partnersinenergie.nl`). Data komt per mail; geen directe download-URL. Vraag vóór de hackathon aan.

### Stedin (o.a. Zuid-Holland, Utrecht, deel Zeeland)

- Open-data pagina: `https://www.stedin.net/zakelijk/open-data`
- **Toegang**: zelfde als Enexis, via Partners in Energie.

### Overige netbeheerders (Coteq, Rendo, Westland Infra)

- Via `https://data.overheid.nl` — zoek op netbeheerder + "kleinverbruik". Beperkt dekkingsgebied.

**Let op vanaf peildatum 1-1-2020**: het standaardjaarverbruik elektriciteit telt alleen de geleverde elektriciteit, niet de teruglevering van zonnepanelen. Elektriciteitsverbruik vóór en na 2020 is niet direct vergelijkbaar. Zie `valkuilen.md`.

---

## 3. Klimaatmonitor (Rijkswaterstaat)

**Wat**: Energieverbruik uitgesplitst naar energiedrager, woningtype en eigendom, energielabels, zonnepanelen en windenergie, tot buurtniveau.

**Toegang**: `https://klimaatmonitor.databank.nl` — HTTP 200 geverifieerd op 2026-06-30.

**Download**: handmatig via de export op de website (kies thema, indicator, geografisch niveau → Exporteren → CSV). Geen stabiele bulk-API gevonden. Download vóór de hackathon en sla op in `data/`.

---

## 4. EP-Online energielabels (RVO)

**Wat**: Energielabel (A t/m G), energieprestatie-indicator en labelklasse per adres (BAG).

**Toegang**:
- Bulk via `https://ep-online.nl/PublicData` — vereist een gratis API-key via `https://www.ep-online.nl/PublicData/Account` (activatie duurt enkele minuten). Vraag vooraf aan.
- Alternatief: Energielabel-API van `https://api.overheid.io/v3/energielabels/{bagid}` — vereist een gratis API-key (api.overheid.io). Reageert met HTTP 401 zonder key (geverifieerd).

**Aggregatie naar buurt**: koppel via postcode (PC6) of BAG-verblijfsobject naar buurtcode, daarna aggregeren.

**Licentie**: open data.

**Aandachtspunt**: energielabels kennen selectiebias — zie `valkuilen.md` punt 4.

---

## 5. Kadaster / CBS koopprijzen

**Wat**: Prijsindex Bestaande Koopwoningen (CBS/Kadaster, kwaliteitsgecorrigeerd) en gemiddelde koopsom. Maandelijkse publicatie.

**Geografisch niveau**: nationaal en provinciaal via open kanalen. Niet op buurtniveau zonder StatLine.

**Toegang**: Vastgoeddashboard op `https://www.kadaster.nl/zakelijk/producten/woningmarkt/vastgoeddashboard`.

**Voor woningwaarde per buurt**: gebruik `gemiddeldeWoningwaarde` uit de PDOK-buurtkaart (gemiddelde WOZ per woning, × €1.000).

**Aandachtspunt**: de gemiddelde koopsom is geen prijsindicator over de tijd — gebruik de Prijsindex Bestaande Koopwoningen. Zie `valkuilen.md` punt 6.

---

## 6. PDOK Locatieserver (PC6-centroïden)

**Wat**: Geocodeerservice van PDOK; geeft de centroïde-coördinaat bij een postcode. Gebruikt door de ruimtelijke PC6→buurt-route.

**Endpoint** (geverifieerd, HTTP 200):
```
https://api.pdok.nl/bzk/locatieserver/search/v3_1/free?q={pc6}&rows=1&fl=centroide_ll&fq=type:postcode
```
Retourneert `centroide_ll` als WKT-punt, bijv. `POINT(4.90185421 52.37289416)` voor `1011EA`.

---

## 7. data.overheid.nl

**Wat**: Catalogus van Nederlandse open datasets. Startpunt voor aanvullende of regionale bronnen.

**Toegang**: `https://data.overheid.nl` — HTTP 200 geverifieerd op 2026-06-30.

**Gebruik**: als een thema niet door bovenstaande bronnen wordt gedekt, zoek hier op trefwoord en kijk in dataset-beschrijvingen voor directe download-URL's.
