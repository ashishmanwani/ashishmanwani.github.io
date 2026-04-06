#!/bin/bash
# Seed the proxy pool based on the configured provider.
# Run inside the API container: docker compose exec api bash scripts/seed_proxies.sh

set -e

echo "Seeding proxy pool..."

PROVIDER="${PROXY_PROVIDER:-none}"

case "$PROVIDER" in
  webshare)
    echo "Loading proxies from Webshare API..."
    python -c "
from proxy.sources.webshare import fetch_and_load_proxies
count = fetch_and_load_proxies()
print(f'Loaded {count} proxies from Webshare')
"
    ;;
  static_file)
    echo "Loading proxies from static file: ${PROXY_STATIC_FILE_PATH}"
    python -c "
import os
from proxy.sources.static_list import load_from_file
path = os.environ.get('PROXY_STATIC_FILE_PATH', '/app/proxies.txt')
count = load_from_file(path)
print(f'Loaded {count} proxies from {path}')
"
    ;;
  none)
    echo "PROXY_PROVIDER=none. No proxies loaded. Scraping will use direct connections."
    echo "Note: Amazon will likely block direct connections. Set PROXY_PROVIDER=webshare or static_file."
    ;;
  *)
    echo "Unknown PROXY_PROVIDER: $PROVIDER"
    exit 1
    ;;
esac

echo "Done."
