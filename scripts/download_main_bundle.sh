#!/usr/bin/env bash
set -euo pipefail

DESI_BASE="https://data.desi.lbl.gov/public/dr1/vac/dr1/mws/iron/v1.0/rv_output/240521"
ZENODO_CORRECTION="https://zenodo.org/records/15469272/files/backup_correction.fits?download=1"
MAIN_OUT="${1:-data/desi_main}"
CORRECTION_OUT="${2:-data/desi_corrections}"

mkdir -p "$MAIN_OUT" "$CORRECTION_OUT"

main_files=(
  "rvpix_exp-main-backup.fits"
  "rvpix_exp-main-bright.fits"
  "rvpix_exp-main-dark.fits"
)

for file in "${main_files[@]}"; do
  echo "Downloading $file"
  curl --fail --location --continue-at - "$DESI_BASE/$file" --output "$MAIN_OUT/$file"
done

echo "Downloading backup correction"
curl --fail --location --continue-at - "$ZENODO_CORRECTION" \
  --output "$CORRECTION_OUT/backup_correction.fits"

echo "MAIN bundle downloaded to $MAIN_OUT"
echo "Backup correction downloaded to $CORRECTION_OUT/backup_correction.fits"
