# sinarsolusi

This repository is now structured to support future monorepo growth.

The current production website lives in `apps/website`.

## Current app

- Public marketing website: `apps/website`

## Local development

Run commands from `apps/website`:

```bash
cd apps/website
npm install
npm run dev
```

Use Node.js `24.14.1` or another Node 24 release that satisfies `apps/website/package.json`.

## Deployment

For Vercel, set the project Root Directory to `apps/website`.
