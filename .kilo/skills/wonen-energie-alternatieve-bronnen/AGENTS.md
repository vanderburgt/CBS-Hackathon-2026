# wonen-energie-alternatieve-bronnen Skill

AI-agent-skill voor journalistiek onderzoek naar wonen en energie met open overheidsdata buiten CBS StatLine om. Terugval bij uitval van StatLine, en aanvullende tweede bron.

## Projectstructuur

- `SKILL.md` — Skill-definitie (wanneer/hoe, werkwijze, output-contract)
- `references/bronnen.md` — Bronnen met URL, formaat, toegang, licentie
- `references/kolomnamen.md` — Exacte kolomnamen + jaarmatrix per bron
- `references/recepten.md` — Vijf koppelrecepten (recept 1 en 4 op echte data getest)
- `references/valkuilen.md` — Dertien veelgemaakte fouten
- `references/geo-koppeling.md` — Drie routes PC6 → buurt
- `scripts/` — `download_bronnen.py`, `pc6_naar_buurt.py`, `maak_top15.py`

## Testen

```bash
pip install -r requirements.txt
python scripts/download_bronnen.py --out data --pdok-jaar 2023
# Recept 1 reproduceren: zie references/recepten.md
```

Pass-criterium: `download_bronnen.py` haalt de PDOK-buurtkaart en Liander binnen, en recept 1 reproduceert het landelijk gasgemiddelde van ~990 m³/jaar (PDOK 2023).
