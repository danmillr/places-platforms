# MTA Turnstile and Ridership Data

**Status: Shell.** Structure, data sources, and pipeline notes are here; working code is not yet built.

## What you will build

A pandas notebook that loads MTA ridership data, cleans it, joins station names to coordinates, and produces station-level ridership summaries and visualizations (time series, station rankings, hour-of-day patterns, choropleth by station).

## The data landscape (important)

**The classic turnstile dataset was retired in 2022.** Anything you find in tutorials from 2018-2021 references a different feed.

**Current sources:**

- **MTA Subway Hourly Ridership: Beginning July 2020** (SODA API + CSV)
  https://data.ny.gov/Transportation/MTA-Subway-Hourly-Ridership-Beginning-July-2020/wujg-7c2s
  Rows are per-hour, per-station-complex, per-payment-method. This is the successor to turnstile data. Preferred for anything current.

- **MTA Subway Stations (with coordinates)**
  https://data.ny.gov/Transportation/MTA-Subway-Stations/39hk-dx4f

- **Legacy turnstile files (weekly txt, 2010 to 2022)**
  http://web.mta.info/developers/turnstile.html
  Use only if you need pre-July-2020 data.

- **NYC Open Data mirrors:** most of the above are also on https://data.cityofnewyork.us/

## Prerequisites

- Python 3.10+ with pandas, geopandas, matplotlib, contextily
- ~2 GB free disk if you download a full year of hourly data (about 40M rows)
- Basic pandas familiarity

## Walkthrough (outline)

### 1. Pull data from SODA

```python
import pandas as pd
url = (
    "https://data.ny.gov/resource/wujg-7c2s.csv"
    "?$where=transit_timestamp between '2026-05-01T00:00:00' and '2026-05-07T23:59:59'"
    "&$limit=5000000"
)
df = pd.read_csv(url, parse_dates=["transit_timestamp"])
```

Filter by date range at the API. Fetching a full year unfiltered will time out.

### 2. Clean and pivot

```python
df["hour"] = df.transit_timestamp.dt.hour
df["dow"] = df.transit_timestamp.dt.day_name()

by_station = df.groupby("station_complex")["ridership"].sum().sort_values(ascending=False)
```

### 3. Join to station coordinates

```python
stations = pd.read_csv("https://data.ny.gov/resource/39hk-dx4f.csv?$limit=1000")
merged = by_station.reset_index().merge(
    stations[["complex_id", "gtfs_latitude", "gtfs_longitude"]],
    left_on="station_complex",
    right_on="complex_id",
)
```

The join key is `station_complex` on ridership and `complex_id` on stations. Not always a clean match; some names in the ridership data drift from the stations table. Spot-check.

### 4. Visualize

- **Bar chart:** top 20 stations by ridership.
- **Time series:** hourly ridership at a single station across a week.
- **Heatmap:** day-of-week x hour matrix for a single station.
- **Map:** stations sized by total ridership, using geopandas + contextily basemap.

### 5. Legacy turnstile (if needed)

The old format is cumulative counters. Delta between successive readings gives entries/exits per period. Standard workflow:

```python
df = pd.read_csv("http://web.mta.info/developers/data/nyct/turnstile/turnstile_220521.txt")
df.columns = df.columns.str.strip()
df["dt"] = pd.to_datetime(df.DATE + " " + df.TIME)
df = df.sort_values(["C/A","UNIT","SCP","STATION","dt"])
df["entries_delta"] = df.groupby(["C/A","UNIT","SCP","STATION"]).ENTRIES.diff()
```

Guard against counter resets (huge negatives) and rollovers.

## Extensions

- **Compare pre- and post-COVID** using the July 2020 pivot.
- **Isochrone weighting.** For a given site, weight nearby stations by their ridership.
- **OMNY vs MetroCard mix.** The hourly dataset breaks out payment method; visualize the transition.
- **Anomaly detection.** Flag hours where ridership deviates from the seasonal norm (games, parades, blackouts).
- **Web dashboard.** Pipe daily aggregates to a JSON and render with D3 or Chart.js.

## Common pitfalls

- **Timezone.** `transit_timestamp` is in America/New_York wall time, not UTC. Do not blindly convert.
- **Station complex vs station.** Ridership is at the complex (all lines at one station). Coordinates in the stations table are per-line entrances. Aggregate before joining.
- **Data drift.** Field names in the SODA API have changed at least twice. Read the current column list before writing SQL.
- **File size.** A single week of hourly data is manageable. A full year is 3+ GB in memory. Filter aggressively or use dask.
- **Complex geography.** Some complexes span two street addresses. If you need entry-level detail, use the legacy turnstile data.
