# Valkuilen

Veelgemaakte fouten bij deze bronnen. Lees dit voordat je een analyse publiceert. Punt 7 t/m 11 zijn live tegen de bestanden vastgesteld en kostten anders zo een uur debuggen.

---

## 1. Standaardjaarverbruik ≠ werkelijk verbruik

Netbeheerdata bevat het **standaardjaarverbruik** (`SJA GEMIDDELD`): het temperatuurgecorrigeerde verbruik, niet wat de klant heeft afgerekend. Schrijf "het gecorrigeerde standaardjaarverbruik bedroeg gemiddeld X m³", niet "bewoners verbruikten X m³".

## 2. Anonimisering: kleine gebieden ontbreken of zijn samengevoegd

Netbeheerdata verschijnt alleen voor gebieden met **minimaal 10 aansluitingen**. Te kleine PC6's worden samengevoegd (`POSTCODE_EIND` wijkt dan af van `POSTCODE`) of ontbreken. Bij aggregatie naar buurt mist daardoor een deel van de buurten. Vermeld dat.

## 3. Elektriciteit vóór en na 2020 niet vergelijkbaar

Vanaf peildatum 1-1-2020 telt het standaardjaarverbruik elektriciteit alleen de **geleverde** stroom, niet de teruglevering van zonnepanelen. Vergelijk je over de grens 2019/2020, vermeld die breuk. Gebruik voor transitietrends bij voorkeur gas (eenvoudiger methodologie).

## 4. Energielabels zijn niet representatief

EP-Online bevat alleen **geregistreerde** labels: oververtegenwoordigd zijn recent verkochte koopwoningen, verhuurde woningen (label verplicht bij verhuur) en nieuwbouw. Conclusies over de gemiddelde energieprestatie van een hele buurt overschatten de werkelijkheid. Zeg "van de woningen met een geregistreerd label" en vermeld de dekkingsgraad.

## 5. Vergelijk altijd binnen hetzelfde woningtype

Een vrijstaande woning verbruikt 2–3× zoveel gas als een appartement. Een buurt met veel appartementen scoort automatisch laag. Dit is geen detail: in recept 1 verklaart woningtype het grootste deel van het verschil tussen sociale-huur- en koopbuurten. Gebruik woningtype-specifieke kolommen (in 2023) of corrigeer expliciet, en vermeld altijd de woningtypeverdeling.

## 6. Koopsom is geen prijsindicator

De gemiddelde koopsom hangt samen met wélke woningen verkocht zijn. Worden in een kwartaal meer grote woningen verkocht, dan stijgt het gemiddelde zonder dat de markt aantrekt. Gebruik voor prijsontwikkeling de **Prijsindex Bestaande Koopwoningen** (Kadaster/CBS).

## 7. `water == 'NEE'`, niet `'N'`

De PDOK-buurtkaart codeert het waterveld als `'NEE'` (land), `'JA'` (water) en `'B'` (deels). Filteren op `water == 'N'` levert **nul rijen** op — een stille fout die je hele analyse leeg maakt. Gebruik `water == 'NEE'`.

## 8. De gaskolom is `gemiddeldAardgasverbruik`, niet `gemiddeldGasverbruikTotaal`

`gemiddeldGasverbruikTotaal` bestaat in het schema maar is in elke jaargang **leeg** (`-99997`). De gevulde gaskolom is `gemiddeldAardgasverbruik`. Wie de verkeerde kiest, krijgt een tabel vol NaN of nul — zonder foutmelding.

## 9. Kolommen verschillen per jaar — kies de juiste jaargang

Gas per woningtype zit alleen in **2023**; zonnestroom, aardgasvrij en stadsverwarming alleen in **2024**; `gemiddeldElektriciteitsverbruikTotaal` is in 2024 leeg (gebruik `gemiddeldeElektriciteitslevering`). Vraag je in één query een kolom op die niet in die jaargang bestaat, dan weigert de WFS het **hele** verzoek met HTTP 400. Zie de jaarmatrix in `kolomnamen.md`. Gebruik bij koppeling dezelfde jaargang voor alle bronnen — buurtgrenzen en -codes wijzigen jaarlijks.

## 10. Sentinelwaarden `-99997` / `-99998`

De buurtkaart gebruikt `-99997` en `-99998` (soms `-99995`) voor ontbrekende/geheime data, voor int én float. Niet wegfilteren betekent dat deze als echte getallen meetellen en je gemiddelden vernielen.
```python
SENTINELS = (-99997, -99998, -99995)
df.loc[df[col].isin(SENTINELS), col] = float("nan")
```

## 11. `pd.qcut` faalt op velden met veel nullen

Heel veel buurten hebben 0% sociale huur, zodat de onderste kwartielgrenzen samenvallen en `pd.qcut(..., q=4)` crasht met "Bin edges must be unique". Gebruik vaste, interpreteerbare klassen (`pd.cut(x, bins=[-0.1, 15, 40, 70, 100.1])`) of `pd.qcut(..., duplicates="drop")`. Vaste klassen zijn ook beter uit te leggen in een verhaal.

## 12. Netbeheerdata dekt niet heel Nederland

Liander dekt circa een derde van het land. Koppel je Liander 2025 aan alle buurten, dan krijgt maar ~37% een waarde (live vastgesteld) — de rest valt buiten het verzorgingsgebied. Voor landelijke dekking heb je ook Enexis en Stedin nodig (aanvraag vooraf). Zonder die: beperk de analyse expliciet tot het Liander-gebied, of gebruik de NL-brede PDOK-buurtkaart (minder detail, maar volledig).

## 13. `meestVoorkomendePostcode` is PC4, geen PC6

Het PDOK-veld `meestVoorkomendePostcode` is een 4-cijferig getal — de meest voorkomende postcode in de buurt, niet dé postcode. De PC4-koppelroute (`scripts/pc6_naar_buurt.py --route pc4`) is daarom een grove benadering: meerdere buurten kunnen dezelfde PC4 delen. Gebruik voor publicatie de ruimtelijke route. Zie `geo-koppeling.md`.
