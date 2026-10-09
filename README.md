# Where did the Melbourne CBD's weekdays go?

Measuring how hybrid work has changed foot traffic in central Melbourne, using the
City of Melbourne Pedestrian Counting System.

**Status:** in progress (started August 2026). Early results are descriptive and
not yet controlled for holidays or weather.

## Question

How much of the CBD's weekday is missing, where, and is the gap closing?

1. How big is the Monday and Friday deficit compared with Tuesday to Thursday?
2. Is that deficit stable, shrinking or growing?
3. Which precincts (office core, retail, university, entertainment) lost the most?
4. Has the shape of the day changed, with flatter commuter peaks and busier evenings?

## Data

| Source | What |
|---|---|
| [CoM Pedestrian Counting System](https://melbournetestbed.opendatasoft.com/explore/dataset/pedestrian-counting-system-monthly-counts-per-hour/) | Hourly counts, about 1.6M rows (rolling 24-month window) |
| [Sensor locations](https://melbournetestbed.opendatasoft.com/explore/dataset/pedestrian-counting-system-sensor-locations/) | Sensor coordinates and status |
| [Victorian public holidays](https://data.gov.au/) | Holiday calendar |
| [BOM weather](http://www.bom.gov.au/climate/data/) | Daily rain and temperature (planned) |

Every data decision is recorded in `CURATION_LOG.md`.

## Plan

- [x] **Stage 1: Build the panel.** Download month by month, verify row counts, keep the 87 of 103 sensors that report every month
- [ ] **Stage 2: Describe the weekday deficit.** Day-of-week and hour-of-day patterns with confidence intervals
- [ ] **Stage 3: Control for confounders.** Holidays, weather and sensor fixed effects
- [ ] **Stage 4: Group sensors into precincts.** By hand, then by clustering daily profiles, and compare
- [ ] **Stage 5: Shape of the day.** Has the morning peak flattened?
- [ ] **Stage 6: Write up.** Answer, confidence, and what would change it

## Early observation (uncontrolled)

Friday mornings are the quietest weekday mornings, while Friday nights run about
57% above midweek. The two roughly cancel in daily totals, which is why most
public analysis misses it. This is not a finding until holidays and weather are
controlled for (Stage 3).

## Reproduce

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python src/fetch_data.py       # downloads raw data into data/raw/
```

Then run the notebooks in `notebooks/` in order.

## Structure

```
data/raw/          downloaded data, never edited (not committed)
data/processed/    cleaned panel (not committed)
notebooks/         analysis, numbered in order
src/               data fetching and processing scripts
CURATION_LOG.md    every data decision and why
```
