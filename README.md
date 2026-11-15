# Olist graph on Grasph: the dump and how to work on it

This folder holds a copy of the Grasph database with the Olist graph, the Grasph server program, and a manual that explains the data.
Grasph has no bolt driver and no GDS library today. You run Grasph on your own computer and work on it there.

## Start

1. Open `olist-graph-manual.html` in a browser and read it. TASK 11.6 has the exact commands to unpack the dump and start the server, for Windows and for a Mac (with Docker).
2. When the server is up, check it: `python grasph_client.py` (Python 3.10 or newer, no extra library). It must print 568,960 nodes and 774,266 relationships.
3. Read `example_first_algorithm.py` and run it (`pip install networkx`). It shows the path from Grasph to one algorithm.
4. From there the work is yours.

## What is in this folder

| Path | What it is |
|---|---|
| `olist-graph-manual.html` | The manual: the data, the schema, how to run and query Grasph. Read this first. |
| `olist-grasph-store.tar.xz` | The dump: the data store of the server (683 MB, 2.8 GB unpacked). |
| `bin/graphdb-server.exe` | The Grasph server program for Windows. |
| `bin/graphdb-server-linux.xz`, `bin/linux-libs.tar.xz` | The Linux program and its libraries, for a Mac with Docker. |
| `grasph_client.py` | Python client: log in, run a query, pull a whole label or relationship type. |
| `example_first_algorithm.py` | One short worked example. |

## Phased analysis (started)

- Full checkbox and tool-execution plan: [analysis/PLAN.md](analysis/PLAN.md).
- First real-data report: [analysis/reports/p2_profile_summary.md](analysis/reports/p2_profile_summary.md).
- Source profiles, hashes and distributions: `analysis/reports/p2_profile.json`.
- Per-column empty/null rates: `analysis/reports/p2_null_rates.csv`.

Run without installing dependencies:

```sh
python3 -m unittest discover -s analysis/tests -v
python3 analysis/tasks/task01_profile.py
```

These results describe the local CSVs, not a verified Grasph export. The cache
puller was replaced to reject truncated queries rather than use unsafe keyset
or ID-window pagination on a server that caps before filtering.

After confirming a local Grasph endpoint, setting `GRASPH_URL`, `GRASPH_USER`,
and `GRASPH_PASSWORD`, and starting the server with the manual's raised limits:

```sh
python3 analysis/pull_cache.py --format jsonl
# Optional after approving/installing pyarrow:
python3 analysis/pull_cache.py --format parquet --cache analysis/cached_parquet
```

The puller checks every table against server counts, validates IDs/endpoints,
writes atomic tables and a hash manifest, and resumes verified tables. Keep the
source dump quiescent: count/hash checks cannot detect equal-size server mutations.
Do not run concurrent exporters into the same cache directory. Live export has
not run in this phase; the previous failed pull log is retained for diagnosis.
