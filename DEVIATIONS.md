# DEVIATIONS.md: Recorded Deviations from BUILD.md

This document tracks all intentional or necessitated deviations from `BUILD.md`, along with the technical justification.

| Item | Specification in BUILD.md | Implemented Behavior | Justification |
|---|---|---|---|
| Python Version | Python 3.12 | Python 3.11 / 3.14 compatibility | Host environment provides Python 3.11 and 3.14. Code is strictly type-hinted with `typing` and compatible across Python 3.11+. |
| Decisions Pending Index | `WHERE stats_counted = false OR true` | `WHERE stats_counted = false` | Per BUILD.md section 3 instructions, the placeholder `OR true` was replaced with the optimized partial index predicate. |
