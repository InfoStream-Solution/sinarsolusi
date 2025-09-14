# Repository Guidelines

## Project Structure & Module Organization
- App Router source in `src/app` (e.g., `layout.tsx`, `page.tsx`).
- Static assets in `public/` (SVG icons, etc.).
- Global styles in `src/app/globals.css` with Tailwind CSS v4 via PostCSS.
- Config: `tsconfig.json` (path alias `@/*` → `src/*`), `next.config.ts`, `postcss.config.mjs`, `eslint.config.mjs`.

## Build, Test, and Development Commands
- `npm run dev` — Start Next.js with Turbopack (hot reload).
- `npm run build` — Production build with Turbopack.
- `npm start` — Run the production server.
- `npm run lint` — Lint the codebase with ESLint.

Run from the repo root. Use Node 18+.

## Coding Style & Naming Conventions
- TypeScript strict mode enabled; prefer explicit types for exports.
- Components: PascalCase (e.g., `MyCard.tsx`); hooks: `useCamelCase`.
- Files in `src/app` follow Next.js routing; keep route folders lowercase.
- Imports: prefer `@/…` alias (e.g., `import Button from '@/components/Button'`).
- ESLint extends `next/core-web-vitals` and `next/typescript`; fix issues or justify with comments.

## Testing Guidelines
- No test framework configured yet. If adding tests:
  - Unit: Vitest/Jest; place as `*.test.ts(x)` near sources or under `src/__tests__/`.
  - E2E: Playwright; store under `e2e/`.
  - Aim for meaningful coverage on components, hooks, and route actions.
- Ensure `npm run lint` passes before opening a PR.

## Commit & Pull Request Guidelines
- Commits are concise, sentence‑case imperative (see Git history). Example: `Add hero section and CTA`.
- Group related changes; avoid noisy formatting‑only commits unless intentional.
- PRs include:
  - Clear description of change and rationale.
  - Linked issue (e.g., `Closes #123`).
  - Screenshots/GIFs for UI changes.
  - Notes on accessibility or performance impacts, if any.

## Security & Configuration Tips
- Place secrets in `.env.local`; do not commit env files. Access via `process.env.*`.
- Review `next.config.ts` before enabling experimental features.
- Validate external inputs in any server actions or API routes.
