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

## Scripts

- `npm run dev` - Start Next.js with Turbopack
- `npm run build` - Build for production
- `npm start` - Start the production server
- `npm run lint` - Run ESLint
- `npm run typecheck` - Run TypeScript checks
