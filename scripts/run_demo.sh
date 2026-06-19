#!/usr/bin/env bash
set -euo pipefail
python -m desi_rv_audit.cli analyze data/synthetic_epochs.csv --output-dir outputs/demo
python -m desi_rv_audit.cli report \
  --source-summary outputs/demo/source_summary.csv \
  --pairs outputs/demo/pairs.csv \
  --output reports/demo_report.md
pytest
