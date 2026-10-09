# Data notes

Everything here was verified against the live API on **3 August 2026**, not
taken from documentation. Where the documentation and the data disagree, the
data wins and it's noted below.

---

## 1. The window is 24 months, not 17 years

Every write-up of this dataset — including the City of Melbourne's own page —
says hourly counts are available **"since 2009."** They are not, at least not
through any currently published endpoint.

```
records:      1,612,972
date range:   2024-08-03  ->  2026-08-02
years present: 2024, 2025, 2026 only
```

It is a **rolling 24-month window**. Old data is dropped as new data arrives.

Consequences you must accept:

- **There is no pre-COVID baseline available.** Any claim of the form "footfall
  is X% below 2019" cannot be made from this data. Don't make it.
- **The window moves.** Re-running `fetch_data.py` in three months gives you a
  different range, not a longer one. Keep `data/raw/` and the `FETCHED_AT.txt`
  stamp if you want your numbers to stay reproducible.
- The legacy Socrata endpoint (`data.melbourne.vic.gov.au/resource/b2ak-trbp`)
  that older tutorials use is **dead — returns 404.** Any Stack Overflow answer
  or blog post using it is stale.

If you later want the historical series, the known partial mirrors are a
[Zenodo archive](https://zenodo.org/records/4656626) (small research subset,
2009–2020) and various Kaggle re-uploads of unclear provenance. Treat both as
untrusted until you've checked them against something. Alternatively the City of
Melbourne will usually respond to a direct data request.

**This reframes the project and that's fine.** Two years of hourly data across
100 sensors is a genuinely rich panel. The question shifts from "recovery
versus 2019" to "the structure of the weekday now, and whether it's moving" —
which was always the more interesting question anyway.

---

## 2. Schema

**`pedestrian_counts.parquet`** — 1,612,972 rows

| column | type | notes |
|---|---|---|
| `id` | int | synthetic row id, `location_id` + hour + date concatenated |
| `location_id` | int | join key to sensors. **103 distinct** |
| `sensing_date` | date | |
| `hourday` | int | 0–23 |
| `direction_1` | int | |
| `direction_2` | int | |
| `pedestriancount` | int | = direction_1 + direction_2 |
| `sensor_name` | str | **25,639 nulls** |
| `location` | struct | lat/lon. Same 25,639 nulls |

**`sensor_locations.parquet`** — 134 rows, incl. `installation_date`,
`sensor_description`, `status`, lat/lon, direction labels.

### Join asymmetry — check this before you join

**103** sensors appear in the counts; **134** in the locations table. The extra
31 are decommissioned units still listed. Meanwhile 25,639 count rows have a
null `sensor_name`, meaning some counting sensors aren't fully described in the
locations table.

An inner join silently drops rows. A left join gives you nulls you must then
handle. Neither is wrong — but decide deliberately and write down which you did.

---

## 3. Sensor churn is real and it will fool you

Distinct sensors reporting per month rises over the window:

```
2024-08:  94 sensors      2025-08: 100
2024-12:  95              2025-11: 102   <- peak
2025-04:  98              2026-08:  98
```

**A ~9% increase in sensor count across the window.** Sum raw counts across all
sensors by month and you will "discover" that Melbourne's foot traffic grew.
You will have discovered that the council installed more sensors.

**The fix used here:** restrict to sensors present in all 25 months.

```
balanced panel:  87 of 103 sensors
coverage:        1,441,236 rows of 1,524,240 possible = 94.6% complete
```

The remaining 5.4% is genuine sensor downtime. **Missing hours are absent rows,
not zero rows** — if you reindex onto a full hourly grid and `fillna(0)` you
will manufacture a decline out of maintenance windows.

---

## 4. The finding that justifies the whole project

Daily totals for the balanced panel, averaged by weekday:

```
Mon  689k   -12.4%  vs Tue-Thu
Tue  763k
Wed  780k
Thu  817k
Fri  841k    +6.9%   <-- Friday is BUSIER than midweek
Sat  847k    +7.7%   <-- Saturday is the busiest day of the week
Sun  694k
```

The standard hybrid-work story predicts Monday *and* Friday are both empty.
The data says Friday is the second-busiest day in the CBD. Taken at face value
that looks like a refutation.

It isn't. Split the same panel by hour:

```
                  Mon      Fri
7-9am    (commute)  -16.9%   -19.7%
5-6pm    (commute)  -15.2%    +1.6%
11am-2pm (midday)    -6.7%    +0.5%
8-11pm   (night)    -23.5%   +56.9%
```

**Friday morning is the emptiest weekday morning of the week — and Friday night
is the busiest weeknight by a huge margin.** The two cancel almost exactly in
the daily total.

So the CBD hasn't lost people. It has swapped commuters for visitors. Daily
totals — which is what essentially all public reporting on this uses — average
that swap into invisibility.

That is the spine of the analysis: **the aggregation everyone uses destroys the
effect everyone is arguing about.**

Two more things worth chasing:

- The Monday deficit is **exactly stable** at -12.4% in both year 1 and year 2.
  Whatever settled Monday into place had already finished before Aug 2024.
- Friday's *surplus* grew, +5.9% → +7.9%, while Tue–Thu volume rose only 2.7%.
  Friday night is doing something the rest of the week isn't.

Neither is confounder-controlled yet. Both could partly be holidays or weather.
That's stage 3.

---

## 5. Still to acquire

- **Victorian public holidays.** Not optional. Melbourne Cup (Tue), AFL Grand
  Final Friday, Easter — these land on specific weekdays and will contaminate
  weekday effects if untreated.
- **BOM daily weather** for Melbourne (station 086338, Olympic Park). Rain
  suppresses foot traffic sharply and is not evenly distributed across weekdays
  in a two-year sample.
- **Major events calendar.** AFL fixtures at the MCG/Marvel, Grand Prix, White
  Night. Mostly matters for outlier explanation and for the residual-model
  extension.
- **Precinct labels for the 87 balanced-panel sensors.** Hand-label these
  yourself from local knowledge — office core / retail / university /
  entertainment / transport interchange. It takes twenty minutes and it's the
  input to stage 4.
