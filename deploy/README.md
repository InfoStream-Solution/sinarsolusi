# Deployment Layout

This directory keeps deployment concerns separate from application source.

## Image Flow

- Image target: `ghcr.io/infostream-solution/sinarsolusi_news_scraper`
- `deploy/build/news_scraper.build.sh` builds the scraper image locally.
- `deploy/build/news_scraper.publish.sh` tags and pushes the built image to GHCR.

## Runtime

- `deploy/runtime/news_scraper.pull.sh` pulls the already-published image from GHCR.
- `deploy/runtime/news_scraper.run.sh` runs the already-published image with the app's runtime env file.
- The runtime script defaults to `IMAGE_TAG=latest` and expects `ENV_FILE=/etc/news_scraper.env` unless overridden.
- `deploy/runtime/news_scraper.sync.sh` copies runtime scripts, cron intent, and the Compose file to the server over SSH.
- `apps/news_scraper/compose.yaml` is the source of truth for the runtime env file and host mounts.

## Scheduling

- `ops/cron/news_scraper.seed.hourly` is the cron intent file for hourly seeding.
- The cron entry pulls the GHCR image, then runs it on the host.
- The server-side Compose file owns the host-to-container mounts.

## Example Commands

```bash
IMAGE_NAME=ghcr.io/infostream-solution/sinarsolusi_news_scraper IMAGE_TAG=local-test ./deploy/build/news_scraper.build.sh
SOURCE_TAG=local-test PUBLISH_TAG=tagname IMAGE_NAME=ghcr.io/infostream-solution/sinarsolusi_news_scraper ./deploy/build/news_scraper.publish.sh
IMAGE_NAME=ghcr.io/infostream-solution/sinarsolusi_news_scraper IMAGE_TAG=tagname ENV_FILE=/etc/news_scraper.env ./deploy/runtime/news_scraper.run.sh
```
