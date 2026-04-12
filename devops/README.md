# Deployment Layout

This directory keeps deployment concerns separate from application source.

## Image Flow

- Image target: `ghcr.io/infostream-solution/sinarsolusi_news_scraper`
- `devops/scripts/news_scraper.build.sh` is the build script for the scraper image.
- `devops/scripts/news_scraper.publish.sh` is the publish script that tags and pushes the built image to GHCR.

## Runtime

- `devops/scripts/news_scraper.pull.sh` is the pull script for the already-published image.
- `devops/scripts/news_scraper.run.sh` is the runtime script that runs the already-published image with the server runtime stack.
  - With no arguments it defaults to `seed kompas.com`.
  - Pass `extract-news kompas.com` or another command to run a different pipeline step.
- The runtime script defaults to `IMAGE_TAG=latest` and expects `ENV_FILE=/etc/news_scraper.env` unless overridden.
- `devops/runtime/news_scraper.compose.yaml` is the source of truth for host mounts and container path mapping.
- `devops/runtime/news_scraper.env.example` documents the server-side runtime flags that belong in `/etc/news_scraper.env`.

## Local vs Server

Use different runtime env files for local and server container runs:

- Local: use a repo-local env file such as `.env.news_scraper`.
- Server: use `/etc/news_scraper.env`.

Examples:

```bash
IMAGE_NAME=ghcr.io/infostream-solution/sinarsolusi_news_scraper IMAGE_TAG=local-test ENV_FILE="$PWD/.env.news_scraper" ./devops/scripts/news_scraper.run.sh seed kompas.com
```

```bash
IMAGE_NAME=ghcr.io/infostream-solution/sinarsolusi_news_scraper IMAGE_TAG=latest ENV_FILE=/etc/news_scraper.env ./devops/scripts/news_scraper.run.sh seed kompas.com
```

If you call `docker compose` directly, remember that `env_file` paths are resolved relative to `devops/runtime/news_scraper.compose.yaml`.

## Scheduling

- `devops/cron/news_scraper.seed.hourly` is the cron intent file for hourly seeding.
- The cron entry pulls the GHCR image, then runs it on the host.
- The server-side Compose file owns the host-to-container mounts.

## Server Bootstrap

On a new server, run the one-time bootstrap script to create the host data directories used by the Compose mounts:

```bash
DATA_ROOT=/var/lib/sinarsolusi bash ./devops/scripts/news_scraper.install.sh
```

This creates:

```text
/var/lib/sinarsolusi/
├── content/
├── links/
├── scraped/
└── seed/
```

If you use a different deploy user or data root, override `DEPLOY_USER` and `DATA_ROOT` accordingly. By default it uses the current user running the script, or `SUDO_USER` when invoked via `sudo`.

## Example Commands

```bash
IMAGE_NAME=ghcr.io/infostream-solution/sinarsolusi_news_scraper IMAGE_TAG=local-test ./devops/scripts/news_scraper.build.sh
SOURCE_TAG=local-test PUBLISH_TAG=tagname IMAGE_NAME=ghcr.io/infostream-solution/sinarsolusi_news_scraper ./devops/scripts/news_scraper.publish.sh
IMAGE_NAME=ghcr.io/infostream-solution/sinarsolusi_news_scraper IMAGE_TAG=tagname ENV_FILE=/etc/news_scraper.env ./devops/scripts/news_scraper.run.sh
IMAGE_NAME=ghcr.io/infostream-solution/sinarsolusi_news_scraper IMAGE_TAG=tagname ENV_FILE=/etc/news_scraper.env ./devops/scripts/news_scraper.run.sh extract-news kompas.com
IMAGE_NAME=ghcr.io/infostream-solution/sinarsolusi_news_scraper IMAGE_TAG=tagname ENV_FILE=../../.env.news_scraper docker compose -f devops/runtime/news_scraper.compose.yaml run --rm news-scraper seed kompas.com
```

The server env file should stay runtime-only:

```text
SCRAPER_DEBUG=0
KEEP_SEED=0
KEEP_SCRAPED=0
```

Container paths and host mounts belong in `devops/runtime/news_scraper.compose.yaml`, not in `/etc/news_scraper.env`.
