#!/usr/bin/env bash
# Controleert de live website: alle adressen uit site/sitemap.xml moeten bereikbaar zijn (200),
# en de regels uit .github/site-checks.txt moeten kloppen. Resultaat als annotatie + job summary.
set -u
BASE="https://mariodigital.eu"
UA="MarioDigital-sitecheck (GitHub Actions)"
ok=0; bad=0; report=""
add() { report+="$1"$'\n'; }

fetch() { # url -> zet $code en $body
  body=$(curl -sS -L --max-time 20 -A "$UA" -w $'\n%{http_code}' "$1" 2>/dev/null)
  code="${body##*$'\n'}"; body="${body%$'\n'*}"
}

# 1. Alle adressen uit de sitemap
for url in $(grep -o '<loc>[^<]*</loc>' site/sitemap.xml | sed 's/<[^>]*>//g'); do
  fetch "$url"
  if [ "$code" = "200" ]; then ok=$((ok+1)); add "OK   $code $url"; else bad=$((bad+1)); add "FOUT $code $url"; fi
done

# 2. Inhoudscontroles
while IFS= read -r line; do
  case "$line" in ''|\#*) continue;; esac
  if [[ "$line" == !* ]]; then
    url="${line#!}"; url="${url%% *}"
    fetch "$url"
    if [ "$code" = "404" ]; then ok=$((ok+1)); add "OK   404 $url (bestaat terecht niet)"; else bad=$((bad+1)); add "FOUT $code $url (zou niet mogen bestaan)"; fi
    continue
  fi
  url="$(echo "${line%%|*}" | xargs)"; want="$(echo "${line#*|}" | xargs)"
  fetch "$url"
  if [ "$code" = "200" ] && grep -qF "$want" <<<"$body"; then ok=$((ok+1)); add "OK   $code $url bevat \"$want\""
  else bad=$((bad+1)); add "FOUT $code $url mist \"$want\""; fi
done < .github/site-checks.txt

summary="Websitecontrole: $ok goed, $bad fout"
{ echo "## $summary"; echo '```'; printf '%s' "$report"; echo '```'; } >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
msg=$(printf '%s\n%s' "$summary" "$report" | sed ':a;N;$!ba;s/%/%25/g;s/\r/%0D/g;s/\n/%0A/g')
if [ "$bad" -gt 0 ]; then echo "::error title=Websitecontrole::$msg"; exit 1; else echo "::notice title=Websitecontrole::$msg"; fi
