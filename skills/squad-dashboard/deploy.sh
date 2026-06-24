#!/usr/bin/env bash
# squad-dashboard — deploy a squad's built dashboard to Netlify (NSLS team).
#
# Usage:  ./deploy.sh <squad-workspace-dir>
#   e.g.  ./deploy.sh ~/squad-dashboards/shop
#
# Reads netlify.site_id (and optional "gated": true) from <dir>/config.json.
# Stages a clean publish dir (index.html + assets/ + optional _headers — nothing else),
# deploys with --no-build (fresh NSLS-team sites auto-assign a `hugo` build command that
# otherwise fails the deploy), and — if the site is SSO-gated — verifies the gate survived.
set -euo pipefail

DIR="${1:?usage: deploy.sh <squad-workspace-dir>}"
DIR="${DIR/#\~/$HOME}"
CONFIG="$DIR/config.json"
[ -f "$CONFIG" ] || { echo "❌ no config.json in $DIR"; exit 1; }
[ -f "$DIR/index.html" ] || { echo "❌ no index.html in $DIR — build it first"; exit 1; }

SITE=$(node -e "console.log((require('$CONFIG').netlify||{}).site_id||'')")
URL=$(node -e "console.log((require('$CONFIG').netlify||{}).url||'')")
GATED=$(node -e "console.log(require('$CONFIG').gated?'1':'')")
[ -n "$SITE" ] || { echo "❌ config.netlify.site_id is empty — create the site first (netlify sites:create --account-slug kprentiss-ryj1oi0)"; exit 1; }

STAGE="$(mktemp -d)/publish"
mkdir -p "$STAGE"
cp "$DIR/index.html" "$STAGE/index.html"
[ -f "$DIR/_headers" ] && cp "$DIR/_headers" "$STAGE/_headers"
[ -d "$DIR/assets" ] && cp -R "$DIR/assets" "$STAGE/assets"
echo "Staged publish dir for '$(basename "$DIR")'."

# Deploy from the squad dir (so any netlify/edge-functions bundle for gated sites); --no-build skips auto hugo.
( cd "$DIR" && netlify deploy --dir="$STAGE" --prod --no-build --site "$SITE" )

if [ -n "$GATED" ] && [ -n "$URL" ]; then
  sleep 4
  LOC="$(curl -sI "$URL/" | tr -d '\r' | grep -i '^location:' | sed 's/location: //I' || true)"
  if echo "$LOC" | grep -qi '/auth/login'; then
    echo "✅ SSO gate live:  / → $LOC"
  else
    echo "❌ GATE NOT ACTIVE — / did not redirect to /auth/login (got: '${LOC:-<none>}'). Edge functions may not have bundled. Roll back in Netlify."
    exit 1
  fi
else
  echo "✅ Deployed: ${URL:-(see Netlify output above)}"
fi
