#!/bin/sh
set -eu

# Defaults (can be overridden by env)
PBF_PATH="${PBF_PATH:-/data/sudeste-251019.osm.pbf}"
OSRM_PROFILE="${OSRM_PROFILE:-car}"
OSRM_ALGORITHM="${OSRM_ALGORITHM:-ch}"

PBF="$PBF_PATH"
BASE="${PBF%.osm.pbf}.osrm"
PROFILE="/opt/${OSRM_PROFILE}.lua"

echo "==> Using PBF:      $PBF"
echo "==> Base:           $BASE"
echo "==> Profile:        $PROFILE"
echo "==> Algorithm:      ${OSRM_ALGORITHM}"

if [ ! -f "$PBF" ]; then
  echo "ERROR: $PBF not found inside the container"
  ls -l /data || true
  exit 2
fi

# 1) Extract (idempotent)
if [ ! -f "$BASE" ]; then
  echo "==> Running osrm-extract ..."
  osrm-extract -p "$PROFILE" "$PBF"
else
  echo "==> Extract artifacts exist, skipping."
fi

# 2) Prepare graph + 3) Serve
if [ "$OSRM_ALGORITHM" = "mld" ]; then
  if [ ! -f "${BASE}.partition" ] || [ ! -f "${BASE}.cells" ]; then
    echo "==> Running osrm-partition + osrm-customize ..."
    osrm-partition "$BASE"
    osrm-customize "$BASE"
  else
    echo "==> MLD artifacts exist, skipping."
  fi
  echo "==> Starting osrm-routed (MLD) on :5000 ..."
  exec osrm-routed --algorithm mld "$BASE"
else
  if [ ! -f "${BASE}.hsgr" ]; then
    echo "==> Running osrm-contract ..."
    osrm-contract "$BASE"
  else
    echo "==> CH artifacts exist, skipping."
  fi
  echo "==> Starting osrm-routed (CH) on :5000 ..."
  exec osrm-routed --algorithm ch "$BASE"
fi
