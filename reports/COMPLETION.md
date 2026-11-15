# Completion status (verified by script output)

| Phase | Status | Evidence |
|---|---|---|
| P0 discovery | DONE | manual read; platform API token + counts; Docker probe |
| P1 extraction/cache | PARTIAL | pull_cache.py hardened (tests pass). Local server start under Rosetta did not complete (documented). Live server auth intermittent. Source CSVs verified 0-diff to graph per manual TASK 11.5/11.6. |
| P2 profiling | DONE | `python3 analysis/tasks/task01_profile.py` → 41 checks/0 failures; reports/p2_* |
| P3 projections | DONE (bugfixed) | `python3 analysis/tasks/task03_projections.py` → 9 projections + manifests |
| P4 graph algos | DONE | `analysis/.venv/bin/python analysis/tasks/task04_graph_algorithms.py` |
| Proofs | DONE (14/14) | `python3 analysis/proofs.py` → reports/p_math_proofs.md |
| P5 link prediction | DONE | `python3 analysis/tasks/task05_link_prediction.py` |
| P6 tabular ML | DONE | `analysis/.venv/bin/python analysis/tasks/task06_ml.py` |
| P7 NLP | DONE | `python3 analysis/tasks/task07_nlp.py` |
| P8 time/space | DONE | `python3 analysis/tasks/task08_timeseries_spatial.py` |
| P10 synthesis | DONE | reports/SYNTHESIS.md (Q1–Q14), reports/GRASP_PLATFORM_TIPS.md |

Reproduce order (system python3 + venv):
```
python3 analysis/proofs.py
python3 analysis/tasks/task01_profile.py
python3 analysis/tasks/task03_projections.py
python3 analysis/tasks/task05_link_prediction.py
python3 analysis/tasks/task07_nlp.py
python3 analysis/tasks/task08_timeseries_spatial.py
python3 analysis/tasks/task09_grasph_verify.py
analysis/.venv/bin/python analysis/tasks/task02_powerlaw.py
analysis/.venv/bin/python analysis/tasks/task04_graph_algorithms.py
analysis/.venv/bin/python analysis/tasks/task06_ml.py
```
