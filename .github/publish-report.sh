#!/usr/bin/env bash
# Отчёт задания CI (журналы, скриншоты) → служебная ветка ci-report-<ветка>-<задание>.
#   bash .github/publish-report.sh <папка> <задание>
set -euo pipefail
dir=$1 job=$2
mkdir -p "$dir"
echo "$job ${GITHUB_SHA} ${GITHUB_RUN_ID}" > "$dir/STATUS"
cd "$dir"
git init -q -b report
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add -A
git commit -q -m "Отчёт ${job} ${GITHUB_SHA::7}" || exit 0
git push -q -f "https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}.git" \
  "HEAD:ci-report-${GITHUB_REF_NAME}-${job}"
