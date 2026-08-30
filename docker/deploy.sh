#!/usr/bin/env bash
set -Eeuo pipefail

: "${RELEASE_SHA:?RELEASE_SHA is required}"
: "${RELEASE_RUN_ID:?RELEASE_RUN_ID is required}"
: "${RELEASE_ATTEMPT:?RELEASE_ATTEMPT is required}"

if [[ ! "$RELEASE_SHA" =~ ^[0-9a-f]{40}$ ]]; then
    echo "Invalid release SHA." >&2
    exit 1
fi
if [[ ! "$RELEASE_RUN_ID" =~ ^[0-9]+$ || ! "$RELEASE_ATTEMPT" =~ ^[0-9]+$ ]]; then
    echo "Invalid workflow run identifiers." >&2
    exit 1
fi

deployment_root="/opt/classpulse"
release_id="${RELEASE_SHA}-${RELEASE_RUN_ID}-${RELEASE_ATTEMPT}"
release_dir="${deployment_root}/releases/${release_id}"
environment_file="${deployment_root}/shared/.env.production"
archive_file="${HOME}/classpulse-${release_id}.tar.gz"

if [[ ! -f "$archive_file" ]]; then
    echo "Release archive was not uploaded." >&2
    exit 1
fi
if [[ ! -f "$environment_file" ]]; then
    echo "Production environment file is missing." >&2
    exit 1
fi

mkdir "$release_dir"
tar --extract --gzip --file "$archive_file" --directory "$release_dir"
ln --symbolic "$environment_file" "${release_dir}/.env.production"

cd "$release_dir"
docker compose --project-name classpulse --env-file "$environment_file" config --quiet
docker compose --project-name classpulse --env-file "$environment_file" build web
docker compose \
    --project-name classpulse \
    --env-file "$environment_file" \
    up --detach --remove-orphans --wait --wait-timeout 180
docker compose \
    --project-name classpulse \
    --env-file "$environment_file" \
    exec -T web python manage.py check </dev/null

site_is_ready=false
for attempt in {1..30}; do
    if curl \
        --fail \
        --silent \
        --show-error \
        --output /dev/null \
        --max-time 5 \
        http://127.0.0.1/; then
        site_is_ready=true
        break
    fi
    echo "Waiting for the public endpoint (${attempt}/30)..."
    sleep 2
done
if [[ "$site_is_ready" != true ]]; then
    echo "Public endpoint did not become healthy." >&2
    exit 1
fi
ln --symbolic --force --no-dereference "$release_id" "${deployment_root}/releases/current"
rm "$archive_file"

echo "Deployed ${RELEASE_SHA}."
