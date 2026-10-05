#!/usr/bin/env bash
# Creates the initial backlog of GitHub issues with the GitHub CLI.
# Usage: gh auth login   (once)   then   bash scripts/create_issues.sh
set -euo pipefail

REPO="nursich/cargo-dispatch"

gh label create "algorithm" --repo "$REPO" --color 5319e7 --description "Allocation logic" 2>/dev/null || true
gh label create "ci" --repo "$REPO" --color 0e8a16 --description "CI/CD pipeline" 2>/dev/null || true

gh issue create --repo "$REPO" --label enhancement --label algorithm \
  --title "Support time windows for pick-up and delivery" \
  --body "Requests often have a latest pick-up time. Add optional \`pickup_before\` / \`deliver_before\` columns and treat pairs that cannot meet them as infeasible."

gh issue create --repo "$REPO" --label enhancement --label algorithm \
  --title "Use real road distances (OSRM) instead of haversine x 1.25" \
  --body "Add an optional distance provider that queries an OSRM server and caches the matrix. Keep haversine as the offline default."

gh issue create --repo "$REPO" --label enhancement --label algorithm \
  --title "Allow a carrier to take several small loads (bin packing)" \
  --body "Today each carrier takes one request per round. Investigate a capacity-aware extension (e.g. MILP with PuLP/OR-Tools) and compare it with the current assignment model."

gh issue create --repo "$REPO" --label enhancement \
  --title "Learn scoring weights from historical dispatcher decisions" \
  --body "Fit weights (cost / reliability / rating) with logistic regression on past accepted vs rejected offers."

gh issue create --repo "$REPO" --label ci \
  --title "Publish documentation site with GitHub Pages" \
  --body "Build API docs with MkDocs + mkdocstrings in CI and deploy them to GitHub Pages on every release."

gh issue create --repo "$REPO" --label bug \
  --title "Map labels overlap when many objects are in one city" \
  --body "Labels are grouped by coordinates, but nearby cities (e.g. Astana / Temirtau) can still overlap. Consider adjustText or a leader-line layout."

echo "Issues created."
