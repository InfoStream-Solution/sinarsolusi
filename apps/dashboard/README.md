# dashboard

`dashboard` is the internal ops app for Sinar Solusi.

It is a separate Next.js application from the public marketing site and the scraper service.

## Getting Started

Run the development server from this directory:

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

Set `DASHBOARD_USERNAME`, `DASHBOARD_PASSWORD`, `DASHBOARD_SESSION_SECRET`,
`SCRAPER_SERVICE_URL`, and `SCRAPER_SERVICE_TOKEN` in your local `.env`
before starting the app. The token must match the scraper service token.

## Container

Build the dashboard container from this directory:

```bash
bash scripts/build_image.sh
docker run --rm -p 3001:3000 --env-file .env ghcr.io/infostream-solution/sinarsolusi_dashboard:<tag>
```

By default the script tags images with a timestamp like `20260419153000`.
Set `IMAGE_TAG=latest` if you want the `latest` tag instead.

To publish the image after building it:

```bash
bash scripts/publish_image.sh
```

Use `SOURCE_TAG` to point at the built timestamp tag and `PUBLISH_TAG` for
the registry tag you want to push.

The app is packaged as a standalone Next.js container and is intended to be
deployed separately from `apps/website` and `apps/news_scraper`.

If the scraper service runs on the host machine, set:

```bash
SCRAPER_SERVICE_URL=http://host.docker.internal:8585
```

On Linux, add the host mapping when running the container:

```bash
docker run --add-host=host.docker.internal:host-gateway ...
```

To run it with Docker Compose:

```bash
docker compose -f devops/runtime/dashboard.compose.yaml up -d --build
```

## Scripts

- `npm run dev` - Start Next.js with Turbopack
- `npm run build` - Build for production
- `npm start` - Start the production server
- `npm run lint` - Run ESLint
- `npm run typecheck` - Run TypeScript checks
