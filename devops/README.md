# Deployment Layout

This directory keeps deployment concerns separate from application source.

## Image Flow

- Image target: `ghcr.io/infostream-solution/sinarsolusi_news_scraper`
- `apps/news_scraper/scripts/build_image.sh` is the developer build script for the scraper image, using the app-local Dockerfile at `apps/news_scraper/Dockerfile`.
- `apps/news_scraper/scripts/publish_image.sh` is the app-local publish script that tags and pushes the built image to GHCR.

## Runtime

- `devops/runtime/news_scraper.compose.yaml` is the server stack definition for `postgres`, `redis`, `web`, `worker`, `beat`, plus the one-off `news-scraper` job service.
- `devops/scripts/news_scraper.pull.sh` is the pull script for the already-published image.
- `devops/scripts/news_scraper.run.sh` is the runtime script that runs the already-published image with the server runtime stack.
  - With no arguments it defaults to `seed kompas.com`.
  - Pass `extract-news kompas.com` or another command to run a different pipeline step.
- `devops/scripts/news_scraper.seed_all.sh` is the server cron wrapper for the seed job.
  - It runs `seed` for `kompas.com`, `detik.com`, and `beritasatu.com` in sequence.
  - It writes timestamped output to `/var/log/news-scraper-seed-all.log`.
  - It must be executable on the server (`chmod +x`).
- `devops/scripts/news_scraper.seed_extract_all.sh` is the server cron wrapper for the combined seed + extract job.
  - It runs `seed` and then `extract-news` for `kompas.com`, `detik.com`, and `beritasatu.com`.
  - It writes timestamped output to `/var/log/news-scraper-seed-extract-all.log`.
  - It must be executable on the server (`chmod +x`).
- The runtime script defaults to `IMAGE_TAG=latest` and expects `ENV_FILE=/etc/news_scraper.env` unless overridden.
- `apps/news_scraper/compose.dev.yaml` is the app-local development stack for local Postgres, Redis, web, worker, and beat containers.
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

Bring up the long-running server stack with:

```bash
IMAGE_NAME=ghcr.io/infostream-solution/sinarsolusi_news_scraper IMAGE_TAG=latest ENV_FILE=/etc/news_scraper.env docker compose -f devops/runtime/news_scraper.compose.yaml up -d
```

## Scheduling

- `devops/cron/news_scraper.seed.hourly` is the cron intent file for scheduled seeding.
- The current schedule is every 5 minutes.
- The cron entry calls the wrapper script, which handles logging and per-domain execution.
- The server-side Compose file owns the host-to-container mounts.

## Server Bootstrap

On a new server, run the one-time bootstrap script to create the host data directories used by the Compose mounts:

```bash
DATA_ROOT=/var/lib/sinarsolusi bash ./devops/scripts/news_scraper.install.sh
```

This creates:

```text
/var/lib/sinarsolusi/
├── postgres/
├── content/
├── links/
├── scraped/
└── seed/
```

If you use a different deploy user or data root, override `DEPLOY_USER` and `DATA_ROOT` accordingly. By default it uses the current user running the script, or `SUDO_USER` when invoked via `sudo`.

## Example Commands

```bash
cd apps/news_scraper && IMAGE_NAME=ghcr.io/infostream-solution/sinarsolusi_news_scraper IMAGE_TAG=local-test bash ./scripts/build_image.sh
cd apps/news_scraper && SOURCE_TAG=local-test PUBLISH_TAG=tagname IMAGE_NAME=ghcr.io/infostream-solution/sinarsolusi_news_scraper bash ./scripts/publish_image.sh
IMAGE_NAME=ghcr.io/infostream-solution/sinarsolusi_news_scraper IMAGE_TAG=tagname ENV_FILE=/etc/news_scraper.env ./devops/scripts/news_scraper.run.sh
IMAGE_NAME=ghcr.io/infostream-solution/sinarsolusi_news_scraper IMAGE_TAG=tagname ENV_FILE=/etc/news_scraper.env ./devops/scripts/news_scraper.run.sh extract-news kompas.com
IMAGE_NAME=ghcr.io/infostream-solution/sinarsolusi_news_scraper IMAGE_TAG=tagname ENV_FILE=/etc/news_scraper.env docker compose -f devops/runtime/news_scraper.compose.yaml up -d
IMAGE_NAME=ghcr.io/infostream-solution/sinarsolusi_news_scraper IMAGE_TAG=tagname ENV_FILE=../../.env.news_scraper docker compose -f devops/runtime/news_scraper.compose.yaml run --rm news-scraper seed kompas.com
./devops/scripts/news_scraper.seed_all.sh
./devops/scripts/news_scraper.seed_extract_all.sh
```

The server env file should stay runtime-only:

```text
SCRAPER_DEBUG=0
KEEP_SEED=0
KEEP_SCRAPED=0
```

Container paths and host mounts belong in `devops/runtime/news_scraper.compose.yaml`, not in `/etc/news_scraper.env`.
