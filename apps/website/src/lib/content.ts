import fs from 'fs';
import path from 'path';

export type Offer = {
  slug: string;
  title: string;
  description?: string;
  thumbnails: string[];
  images: string[];
  body: string;
};

export type LocalizedOffer = {
  slug: { en: string; id: string };
  title: { en: string; id: string };
  description: { en: string; id: string };
  thumbnails: string[];
  images: string[];
  body: { en: string; id: string };
};

const CONTENT_ROOT = path.join(process.cwd(), 'src', 'content', 'offers');

function parseFrontMatter(src: string): { data: Record<string, unknown>; body: string } {
  const fm = src.startsWith('---') ? src.indexOf('\n---', 3) : -1;
  if (fm === -1) return { data: {}, body: src };
  const header = src.slice(3, fm).replace(/\r\n/g, '\n').trimEnd();
  const body = src.slice(fm + 4).replace(/^\s+/, '');
  const lines = header.split('\n');
  const data: Record<string, unknown> = {};
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const m = line.match(/^([A-Za-z0-9_\-]+):\s*(.*)$/);
    if (!m) { i++; continue; }
    const key = m[1];
    const val = m[2];
    // Block list (YAML): key:\n  // - value\n  // - value
    if (val === '' && i + 1 < lines.length && /^\s*-\s+/.test(lines[i + 1])) {
      const arr: string[] = [];
      i++;
      while (i < lines.length && /^\s*-\s+/.test(lines[i])) {
        const item = lines[i].replace(/^\s*-\s+/, '').trim().replace(/^\"|\"$/g, '');
        if (item) arr.push(item);
        i++;
      }
      (data as Record<string, unknown>)[key] = arr;
      continue;
    }
    // Inline array
    if (val.startsWith('[') && val.endsWith(']')) {
      const inner = val.slice(1, -1);
      const arr = inner.split(',').map((s) => s.trim().replace(/^\"|\"$/g, '')).filter(Boolean);
      (data as Record<string, unknown>)[key] = arr;
      i++;
      continue;
    }
    // Scalar
    (data as Record<string, unknown>)[key] = val.replace(/^\"|\"$/g, '');
    i++;
  }
  return { data, body };
}

export function getOffers(): Offer[] {
  const entries = fs.readdirSync(CONTENT_ROOT, { withFileTypes: true });
  const dirs = entries.filter((e) => e.isDirectory());
  const offers: Offer[] = [];
  for (const d of dirs) {
    const slug = d.name;
    const p = path.join(CONTENT_ROOT, slug, 'index.md');
    // prefer localized english if present for title/desc; fall back to index.md for body if no en
    const en = path.join(CONTENT_ROOT, slug, 'index.en.md');
    const hasBase = fs.existsSync(p);
    const hasEn = fs.existsSync(en);
    if (!hasBase && !hasEn) continue;
    const raw = fs.readFileSync(hasBase ? p : en, 'utf8');
    const { data, body } = parseFrontMatter(raw);
    // merge possible english meta
    let title = (data.title as string) || slug;
    let description = (data.description as string) || '';
    if (hasEn) {
      const { data: enData } = parseFrontMatter(fs.readFileSync(en, 'utf8'));
      title = (enData.title as string) || title;
      description = (enData.description as string) || description;
    }
    offers.push({
      slug: (data.slug as string) || slug,
      title,
      description,
      thumbnails: (data.thumbnails as string[]) || [],
      images: (data.images as string[]) || [],
      body,
    });
  }
  return offers;
}

export function getOfferBySlug(slug: string): Offer | null {
  const p = path.join(CONTENT_ROOT, slug, 'index.md');
  const en = path.join(CONTENT_ROOT, slug, 'index.en.md');
  if (!fs.existsSync(p) && !fs.existsSync(en)) return null;
  const base = fs.existsSync(p) ? parseFrontMatter(fs.readFileSync(p, 'utf8')) : { data: {}, body: '' };
  const eng = fs.existsSync(en) ? parseFrontMatter(fs.readFileSync(en, 'utf8')) : { data: {}, body: '' };
  return {
    slug: ((base.data.slug as string) || (eng.data.slug as string)) || slug,
    title: ((eng.data.title as string) || (base.data.title as string)) || slug,
    description: ((eng.data.description as string) || (base.data.description as string)) || '',
    thumbnails: ((base.data.thumbnails as string[]) || (eng.data.thumbnails as string[])) || [],
    images: ((base.data.images as string[]) || (eng.data.images as string[])) || [],
    body: base.body || eng.body,
  };
}

export function getLocalizedOffers(): LocalizedOffer[] {
  const entries = fs.readdirSync(CONTENT_ROOT, { withFileTypes: true });
  const dirs = entries.filter((e) => e.isDirectory());
  const offers: LocalizedOffer[] = [];
  for (const d of dirs) {
    const folder = d.name;
    const pId = path.join(CONTENT_ROOT, folder, 'index.md');
    const pEn = path.join(CONTENT_ROOT, folder, 'index.en.md');
    if (!fs.existsSync(pId) && !fs.existsSync(pEn)) continue;
    const base = fs.existsSync(pId) ? parseFrontMatter(fs.readFileSync(pId, 'utf8')) : { data: {}, body: '' };
    const eng = fs.existsSync(pEn) ? parseFrontMatter(fs.readFileSync(pEn, 'utf8')) : { data: {}, body: '' };
    offers.push({
      slug: {
        id: (base.data.slug as string) || folder,
        en: (eng.data.slug as string) || folder,
      },
      title: {
        id: (base.data.title as string) || folder,
        en: (eng.data.title as string) || (base.data.title as string) || folder,
      },
      description: {
        id: (base.data.description as string) || '',
        en: (eng.data.description as string) || (base.data.description as string) || '',
      },
      thumbnails: ((base.data.thumbnails as string[]) || (eng.data.thumbnails as string[])) || [],
      images: ((base.data.images as string[]) || (eng.data.images as string[])) || [],
      body: {
        id: base.body || eng.body,
        en: eng.body || base.body,
      },
    });
  }
  return offers;
}

export function getOfferByLocaleSlug(locale: 'en' | 'id', slug: string): Offer | null {
  const all = getLocalizedOffers();
  const match = all.find((o) => o.slug[locale] === slug);
  if (!match) return null;
  return {
    slug: match.slug[locale],
    title: match.title[locale],
    description: match.description[locale],
    thumbnails: match.thumbnails,
    images: match.images,
    body: match.body[locale],
  };
}

