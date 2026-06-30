# wonen-energie-alternatieve-bronnen

AI-agent-skill voor journalistiek onderzoek naar wonen en energie met **open overheidsdata buiten CBS StatLine om**. Bedoeld als terugval wanneer StatLine plat ligt, en als onafhankelijke tweede bron daarnaast. Gebouwd voor de CBS-hackathon Wonen & Energie.

De skill koppelt netbeheerdata (verbruik per postcode), de PDOK CBS-buurtkaart, energielabels en koopprijzen tot een scherpe bevinding per buurt, wijk of gemeente — en is eerlijk over de onzekerheid.

## Installatie

Deze repo is opgezet als **standalone skill**: de repository-root ís de skill-map (de mapnaam `wonen-energie-alternatieve-bronnen` komt overeen met het `name`-veld in `SKILL.md`, zoals de [Agent Skills-specificatie](https://agentskills.io/specification) vereist). Daardoor is installeren een drop-in: clone de repo rechtstreeks in je skills-map.

### Kilo (VS Code / CLI)

```bash
# Project-skill (alleen dit project):
git clone https://github.com/linksmith/wonen-energie-alternatieve-bronnen .kilo/skills/wonen-energie-alternatieve-bronnen

# Globale skill (alle projecten):
git clone https://github.com/linksmith/wonen-energie-alternatieve-bronnen ~/.kilo/skills/wonen-energie-alternatieve-bronnen
```

Start daarna een nieuwe sessie — Kilo scant skills bij opstarten. Roep aan met de skillnaam.

### Andere agents / kale terminal

- **Claude Code** — clone naar `~/.claude/skills/wonen-energie-alternatieve-bronnen` of `<project>/.claude/skills/`. De `SKILL.md`-frontmatter is identiek aan wat Claude Code verwacht.
- **Open-agentstandaard (`.agents/skills/`)** — clone naar `~/.agents/skills/wonen-energie-alternatieve-bronnen`.
- **Kale terminal** — draai de scripts direct; ze hebben de agent niet nodig.

## Snel starten

```bash
# 1. Afhankelijkheden (pandas, matplotlib, requests)
pip install -r requirements.txt          # of: uv pip install -r requirements.txt

# 2. Data lokaal ophalen (werk daarna offline)
python scripts/download_bronnen.py --out data --pdok-jaar 2023            # gas (incl. woningtype)
python scripts/download_bronnen.py --out data --geen-liander --pdok-jaar 2024   # zon/aardgasvrij

# 3. Voorbeeld: netbeheer-gas koppelen aan buurten (PC4-benadering) + top-15 diagram
python scripts/pc6_naar_buurt.py --liander data/liander_2025.tsv \
    --pdok data/pdok_buurten_2023.geojson --route pc4 --productsoort GAS \
    --uit data/gas_per_buurt.csv
python scripts/maak_top15.py --csv data/gas_per_buurt.csv \
    --waarde gemiddeldAardgasverbruik --label buurtnaam \
    --titel "Top 15 gasverbruik" --eenheid "m3/jaar" --out data/top15_gas.png
```

## Inhoud

```
SKILL.md                     Wanneer en hoe je de skill gebruikt (progressive disclosure)
references/
  bronnen.md                 Alle bronnen met URL, formaat, toegang, licentie
  kolomnamen.md              Exacte kolomnamen + jaarmatrix (welke kolom in welk jaar gevuld is)
  recepten.md                Vijf koppelrecepten; recept 1 en 4 zijn op echte data gedraaid
  valkuilen.md               De veertien meestgemaakte fouten
  geo-koppeling.md           Drie routes van PC6 naar buurt
scripts/
  download_bronnen.py        Download netbeheer + PDOK-buurtkaart naar data/ (alleen stdlib)
  pc6_naar_buurt.py          PC6->buurt koppeling (pc4 | ruimtelijk | crosswalk) + laad_liander()
  maak_top15.py              Top-15 tabel + staafdiagram met landelijke referentielijn
requirements.txt
```

## Verificatiestatus (2026-06-30)

Alle bronnen zijn live gecontroleerd (HTTP 200). Recept 1 en 4 zijn end-to-end op echte data gedraaid; hun tabellen in `recepten.md` zijn de werkelijke uitkomst. De `data/`-map wordt niet meegecommit (zie `.gitignore`) — haal hem op met `download_bronnen.py`.

## Belangrijkste les uit de verificatie

Vertrouw geen kolomnaam zonder hem tegen een echt bestand te controleren. De buurtkaart filtert op `water == 'NEE'` (niet `'N'`), de gevulde gaskolom is `gemiddeldAardgasverbruik` (niet `gemiddeldGasverbruikTotaal`), en kolommen verschillen per jaargang. Zie `references/valkuilen.md`.
