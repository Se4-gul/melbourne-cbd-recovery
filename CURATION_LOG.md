# Curation log

Every decision made in turning the raw feed into `data/processed/`, and why.
Written so that a reviewer can disagree with a specific choice rather than
having to distrust the whole pipeline.

Entries are in the order the decisions were made. Numbers were verified against
the live API on **3 August 2026**.

---

## 1. Source: the Opendatasoft portal, not the legacy endpoint

**Decision.** Pull from
`melbournetestbed.opendatasoft.com/api/explore/v2.1/`.

**Why.** The Socrata endpoint used by most existing tutorials and blog posts
(`data.melbourne.vic.gov.au/resource/b2ak-trbp`) returns **404**. It is dead.
Any code you find online built on it will not run.

`data.melbourne.vic.gov.au` and `melbournetestbed.opendatasoft.com` both serve
the same 239-dataset catalogue and return identical results; the testbed host
was used throughout.

**Consequence.** If you search for help with this dataset, check the date on the
answer. Anything pre-2023 is likely built on a dead API.

---

## 2. The window is 24 months, and there was no way around it

**Decision.** Accept 2024-08-03 → 2026-08-02 and reframe the question.

**Why.** The City of Melbourne's own documentation states hourly counts are
available "since 2009." Verified against the API, the published dataset contains
only 2024, 2025 and 2026 — a rolling 24-month window, 1,612,972 rows.

Checked for a historical archive and did not find one:

- No archival dataset in either portal's 239-dataset catalogue
- The legacy Socrata endpoint is 404
- data.gov.au entries all redirect to the same rolling export
- A [Zenodo record](https://zenodo.org/records/4656626) exists but is a 4.6 MB
  research subset of unclear coverage, not the full series

**Consequence.** No pre-COVID baseline. Any claim of the form "footfall is X%
below 2019" is unsupportable from this data and must not appear in the writeup.
The question was reframed from *recovery against 2019* to *the structure of the
weekday now* — which is answerable, and arguably the better question anyway.

**Open action.** The City of Melbourne will usually respond to a direct data
request. If the historical series is obtained later, the pre/post comparison
becomes available and this decision should be revisited.

---

## 3. Downloaded month-by-month rather than in one export

**Decision.** 25 separate requests with a `where` date filter, combined locally.

**Why.** The single full export streams very slowly and **silently truncates**.
Two attempts produced 3.1 MB and 5.2 MB files that were both structurally
invalid parquet — but a truncated file that happens to end on a valid boundary
would have loaded fine and silently contained partial data. That is a failure
mode that produces wrong answers with no error message.

Month-sized requests complete in 6–11 seconds each, are individually verifiable,
and make the download resumable.

**Verification.** `src/fetch_data.py` checks for the `PAR1` parquet footer on
every chunk and refuses to write a file without it. Full run reassembles to
exactly 1,612,972 rows, matching the API's own `count(*)`.

---

## 4. Deduplicated on (location_id, sensing_date, hourday)

**Decision.** Drop duplicates on that key after concatenating chunks.

**Why.** Date-range filters at month boundaries are a classic off-by-one source.
The filter used is half-open — `>= month_start AND < next_month_start` — which
should not double-count, but the check is cheap and the failure is silent.

**Result.** Zero duplicates found. The guard stays in because the cost of
keeping it is nil and the cost of it being absent when a boundary bug appears is
a wrong answer.

---

## 5. Balanced panel: 87 of 103 sensors

**Decision.** Restrict all analysis to sensors reporting in **all 25 months**.

**Why.** The sensor network grew over the window:

```
2024-08:  94 sensors  ->  2025-11: 102 (peak)  ->  2026-08: 98
```

That is +8.5% instrumentation growth. Summing raw counts across all sensors by
month produces a rising line that reflects installation activity, not pedestrian
behaviour. This is the single most common misuse of this dataset.

**What it costs.** 16 sensors dropped (~16% of the network), including newer
sensors in areas that may be genuinely interesting. A smaller honest panel was
preferred over a larger one that measures a different city each month.

**Alternative considered.** Sensor fixed effects in a regression handle churn
without dropping anyone, and stage 3 will use exactly that. But for descriptive
statistics — means, bar charts, weekday comparisons — there is no fixed effect
to hide behind, so the balanced panel is required.

**Result.** 1,441,236 rows, 94.6% of the complete sensor × day × hour grid.

---

## 6. Missing hours left missing, never zero-filled

**Decision.** Do not reindex onto a complete hourly grid.

**Why.** An offline sensor produces **no row**, not a zero row. The 5.4% of the
grid that is absent is maintenance downtime, not empty streets. Reindexing and
`fillna(0)` would convert every maintenance window into a period of zero
pedestrians and manufacture a decline.

**Consequence.** Any groupby is over a slightly unbalanced set of hours. For
means this is fine. **For any analysis that sums to a daily total, verify the
day is complete first** — a day missing its 5pm hour will look like a quiet day.

---

## 7. Left join to sensor metadata, not inner

**Decision.** Keep all count rows; accept nulls in `sensor_name` / `location`.

**Why.** The two tables disagree:

- 103 sensors appear in the counts, 134 in the locations table
- 3 sensors have counts but no location record
- 34 have a location record but no counts (decommissioned units still listed)
- 25,639 count rows have a null `sensor_name`

An inner join silently discards those 25,639 rows (1.6% of the data). Dropping
data as a side effect of a join is the wrong default — better to carry the nulls
visibly and decide per-analysis.

**Consequence.** Any string operation on `sensor_name` needs `na=False`.
This bites in practice; see the `str.contains('Fli', na=False)` usage.

---

## 8. Used `pedestriancount`, not the direction fields

**Decision.** Total counts only; `direction_1` / `direction_2` unused.

**Why.** Verified that `direction_1 + direction_2 == pedestriancount` for
**all 1,612,972 rows** — zero exceptions. The directional split is internally
consistent, but nothing in the current questions requires flow direction.

**Open opportunity.** Direction is unexploited and could be interesting:
net inbound flow in the morning versus outbound in the evening would give a
sharper commuter measure than raw volume. Noted for later.

---

## 9. Baseline is Tue–Thu, not the weekly mean

**Decision.** Express every weekday as a deviation from the Tue/Wed/Thu average.

**Why.** The question is about Monday and Friday specifically. A whole-week mean
includes Monday and Friday and so is contaminated by the effect being measured —
a bigger Monday deficit would drag the baseline down and make the deficit look
smaller. Tue–Thu are the days least affected by hybrid schedules, which makes
them the natural comparison.

**Caveat.** This assumes Tue–Thu are themselves unaffected, which is not
strictly true — hybrid work reduces attendance every day. So these figures
measure the *weekday-shape* effect, not the total effect. **Stated as a
limitation, not silently assumed.**

---

## 10. Hour windows chosen a priori

**Decision.** Morning commute 7–9am, evening 5–6pm, midday 11am–2pm, night
8–11pm. Fixed before looking at results.

**Why.** Choosing windows after seeing which ones produce the largest effect is
straightforward p-hacking. These were set from what the windows mean in the
world, not from what they do to the numbers.

**Robustness note.** The finding should not be sensitive to the exact
boundaries. Worth confirming later that 7–10am gives the same story as 7–9am.
Not yet done.

---

## 11. Volume weighting is required when aggregating sensors

**Decision.** Weight by traffic volume when averaging across sensors.

**Why.** Discovered empirically on the five Flinders St sensors:

```
unweighted mean Friday AM deficit:  -25.7%
volume-weighted:                    -28.4%
```

The highest-volume sensor also had the deepest deficit, so treating sensors as
equal units understates the effect. Sensor `Fli114C_T` carries 33 people per
midweek morning; `FliS_T` carries 1,004. Averaging them equally gives the
quietest sensor 30× the influence it deserves.

**Consequence.** Every cross-sensor aggregate from here must state whether it is
weighted. City-wide figures quoted in `DATA_NOTES.md` are currently *unweighted*
and should be recomputed.

---

## 12. Precinct labels: inferred, then adjudicated against the data

**Decision.** Seven categories — office, retail, university, entertainment,
transport, residential, leisure. First pass generated from sensor descriptions
and coordinates, then corrected by local knowledge, with ambiguous cases
resolved empirically.

**Why the labels are a judgement call.** There is no ground truth for "this
sensor is in the office precinct." The labels are a hypothesis about urban
structure, which is exactly why stage 4 clusters sensors independently and
compares. Disagreement between the labels and the clustering is a result, not an
error.

**Confidence is recorded per sensor.** 42 high, 38 med, 7 low at time of
writing. Low-confidence labels should not carry weight in any conclusion.

### Two cases resolved with data rather than argument

**Princes Bridge (id 5)** — ambiguous between transport and leisure.
The discriminating variable turned out to be the weekend ratio:

```
                     wknd_ratio   AM_Fri   commute_share
Princes Bridge             1.33   -16.3%           27.8%
Southern Cross [tra]       0.13   -46.8%           51.2%
Alexandra Gardens [lei]    1.51    -1.5%           27.9%
```

Genuine transport nodes collapse on weekends. Princes Bridge is *busier* on
weekends and has half the commute-hour share of a real transport node →
**leisure**. But its Friday morning deficit (−16.3%) far exceeds pure leisure
sensors (−0.7% to −4.9%), so a real commuter flow exists and is simply
outnumbered. Recorded in the notes rather than erased by the label.

**Flinders Ln & Swanston (id 41)** — proposed as a walk-to-work corridor.
Not supported:

```
                          AM_share   AM_Fri   wknd   FriNight_lift
Flinders Ln & Swanston       12.0%   -10.8%   1.05           +61%
Collins Place [office]       33.2%   -33.4%   0.24           +34%
Degraves cluster [ent]      13-17%  -6..-13%  0.86-1.00  +82..+201%
```

A commuter corridor puts a third of its weekday traffic in the 7–9am window.
This one puts 12%. Kept as **entertainment**, confidence lowered to med.

### An observation that may outrank the labels

Both adjudicated sensors are among the highest-volume in the panel (23.3k and
34.5k per day), and both turned out to be **mixed rather than characteristic**.
The same pattern appeared at Flinders St Station, where the busiest sensor had
the *shallowest* Friday deficit of its group.

Hypothesis worth testing: **the highest-traffic locations are the least
characteristic**, because they capture everyone. If true, volume-weighted
precinct averages will be dominated by sensors that represent no precinct, and a
`thoroughfare` category may be needed. Flagged for stage 4.

### One unexplained anomaly, deliberately left in

`I-Hub Southern Cross Station — Lonsdale St Entrance South` (id 133) has a
weekend ratio of 0.86 and an AM Friday deficit of only −8.8%, while the two
Bourke St entrances to the *same station* behave like a transport node
(0.13–0.58, −42% to −47%). Either the sensor is not capturing station traffic,
or that entrance serves a different population.

Left labelled `transport` with the anomaly recorded. Not resolved. It should
reappear in the clustering, and if it doesn't, that is informative about the
clustering.

---

## 13. Known limitations, not yet addressed

Listed here so they are not mistaken for oversights.

| Gap | Effect on current numbers |
|---|---|
| **No public holiday control** | Good Friday and AFL Grand Final Friday fall on Fridays; Melbourne Cup on a Tuesday. Some of the Friday deficit is holidays. Direction of bias known, magnitude not. |
| **No weather control** | Rain suppresses foot traffic and is not evenly distributed across weekdays in a 2-year sample. Adds noise; could add bias. |
| **No school/university term control** | University-precinct sensors will have large term-break swings unrelated to hybrid work. |
| **No event control** | AFL, Grand Prix, White Night cause large localised spikes. |
| **City-wide figures unweighted** | See §11. Understates the effect. |
| **Hour-window robustness untested** | See §10. |

**None of the current results should be described as findings until at minimum
holidays are controlled.** They are descriptive statistics with a known
confounder that has not been removed.

---

## 14. Public holidays: source selection and a gap in the official data

Work in `notebooks/02_controls.ipynb`. Entry written 3 Aug 2026; the hand-entry
step below was still outstanding at time of writing.

### 14.1 Source: data.gov.au national file, not the Victorian one

**Decision.** Use *Australian Public Holidays Dates Machine Readable Dataset*
from data.gov.au, filtered to `Jurisdiction == "vic"`.

**Why not the Victorian source.** data.vic publishes
[Victorian Government — Important Dates API](https://discover.data.vic.gov.au/dataset/government-dates-api-data),
which sounds like the obvious choice and is not usable:

- The resource named `important-dates-2025.csv` contains **2019** dates
- It mixes public holidays with religious and cultural observances
  (`MULTI_FAITH` rows for Lent, Orthodox Great Lent, etc.) with no clean way to
  isolate gazetted public holidays
- Dates are `d/mm/yyyy` strings, inconsistently zero-padded

Checked and rejected. Noted here so nobody re-evaluates it later.

**Format notes for the national file.** `Date` arrives as `YYYYMMDD` numerics,
not dates — requires `format="%Y%m%d"` and a cast to string. `Jurisdiction` is
lowercase.

### 14.2 The dataset is marked [INACTIVE] and ends at 2025

The panel runs to 2026-08-02. The national file stops at 31 Dec 2025, leaving
**roughly seven months of the window with no holiday coverage** — New Year's Day,
Australia Day, Labour Day, Easter, ANZAC Day and King's Birthday 2026.

Joining this file alone and stopping would treat every 2026 holiday as an
ordinary day, while appearing to have controlled for holidays. That is worse
than no control, because it is invisible.

**Action:** 2026 Victorian dates to be entered by hand from
[business.vic.gov.au](https://business.vic.gov.au/business-information/public-holidays),
tagged with a distinct `source` value so the two origins stay separable.

### 14.3 A missing date that the filter silently discarded

Filtering the Victorian rows to the panel window returned **16 holidays**. The
correct answer is 17.

Row 517 of the national file:

```
ID 524 | Date: NaN | "Friday before the AFL Grand Final"
Information: "Friday before AFL Grand Final typically falls on the last Friday
in September. The Business Victoria website will be updated with the exact date
upon release of the 2025 AFL schedule."
```

The 2025 AFL Grand Final Friday has **no date** in the file — it was published
before the AFL fixture was announced, and never backfilled. It is the **only
null date in the entire five-year, 500+ row national dataset**.

**How it was found.** The `Date` column arrived as `float64` rather than
`int64`. Pandas upcasts integer columns to float to accommodate `NaN`, so the
dtype was the symptom of a single missing value. Investigating why an integer
date field was a float led to the row.

**Why it silently disappeared.** `NaN >= "2024-08-03"` evaluates to `False`, so
a routine date filter dropped it without warning. No error, no count mismatch
that looked implausible — 16 holidays is a perfectly reasonable number.

**Why this row in particular matters.** Of every row in the file that could have
gone missing, this is close to the worst case for this project:

- It falls on a **Friday** — the exact day under investigation
- It is plausibly the one holiday that *raises* CBD morning foot traffic rather
  than lowering it, since the Grand Final parade runs through the city
- It was already flagged in the Step 0 prediction as a mechanism of interest

**Action:** source the 2025 date (last Friday in September 2025) from
business.vic.gov.au and add it with the 2026 entries.

**Process change adopted.** Check `.isna().sum()` on any column before filtering
on it. A comparison filter drops nulls silently; this was a near miss and the
check costs one line.

### 14.4 Consequence for the holiday flag design

Because Grand Final Friday may increase morning traffic while Good Friday,
ANZAC Day and Boxing Day sharply decrease it, a single binary `is_holiday` flag
averages together effects with opposite signs.

**Open question, not yet resolved:** whether to model holiday *type* rather than
a binary. Deferred until the individual holiday-Friday values have been
inspected — see notebook 02 Step 5.

---

## How to use this document

When you write the final analysis, this becomes the methods section. Every
number quoted should be traceable to a decision recorded here, and every
decision should be one a reader could disagree with explicitly.

If you change a decision, **add an entry rather than editing the old one.** The
history of what you tried is more useful than a clean record of what you
settled on.
