import Image from "next/image";
import { notFound } from "next/navigation";
import { getOfferByLocaleSlug, getLocalizedOffers } from "@/lib/content";
import { GalleryMedia } from "./GalleryMedia";

export const revalidate = false;

export async function generateStaticParams() {
  const entries = getLocalizedOffers();
  const params: { slug: string }[] = [];
  for (const o of entries) {
    params.push({ slug: o.slug.en });
    params.push({ slug: o.slug.id });
  }
  return params;
}

export default async function OfferDetail({ params }: { params: Promise<{ locale: 'en'|'id'; slug: string }> }) {
  const { locale, slug } = await params;
  const offer = getOfferByLocaleSlug(locale, slug);
  if (!offer) return notFound();
  const items = offer.images.map((full, i) => ({
    full,
    thumb: offer.thumbnails[i] || full,
    alt: `${offer.title} ${i + 1}`,
  }));
  return (
    <section className="container py-16 md:py-20">
      <h1 className="text-3xl md:text-4xl font-bold text-[color:var(--brand-navy)]">{offer.title}</h1>
      {offer.description && <p className="mt-2 text-neutral-700">{offer.description}</p>}

      {items.length > 0 && (
        <GalleryMedia items={items} layout="carousel" hoverSwap={true} aspect="4/3" />
      )}

      {offer.body && (
        <article
          className="prose prose-neutral max-w-none mt-10 prose-headings:text-[color:var(--brand-navy)] prose-img:w-full prose-img:h-auto"
          dangerouslySetInnerHTML={{ __html: markdownToHtml(offer.body) }}
        />
      )}
    </section>
  );
}

function markdownToHtml(md: string): string {
  const blocks = md.replace(/\r\n/g, '\n').split(/\n\s*\n/);
  const renderInline = (s: string) =>
    s
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code>$1</code>');

  const htmlBlocks: string[] = [];
  for (let block of blocks) {
    const lines = block.split('\n');
    // Headings (single-line)
    if (/^###\s+/.test(lines[0])) {
      htmlBlocks.push(`<h3>${renderInline(lines[0].replace(/^###\s+/, ''))}</h3>`);
      continue;
    }
    if (/^##\s+/.test(lines[0])) {
      htmlBlocks.push(`<h2>${renderInline(lines[0].replace(/^##\s+/, ''))}</h2>`);
      continue;
    }
    if (/^#\s+/.test(lines[0])) {
      htmlBlocks.push(`<h1>${renderInline(lines[0].replace(/^#\s+/, ''))}</h1>`);
      continue;
    }

    // List
    if (lines.every((l) => /^-\s+/.test(l))) {
      const items = lines
        .map((l) => `<li>${renderInline(l.replace(/^-\s+/, ''))}</li>`) 
        .join('');
      htmlBlocks.push(`<ul>${items}</ul>`);
      continue;
    }

    // Images (one per line)
    if (lines.length === 1 && /!\[(.*?)\]\((.*?)\)/.test(lines[0])) {
      const m = lines[0].match(/!\[(.*?)\]\((.*?)\)/);
      if (m) {
        htmlBlocks.push(`<img alt="${m[1]}" src="${m[2]}" />`);
        continue;
      }
    }

    // Paragraph (join and render inline)
    htmlBlocks.push(`<p>${renderInline(lines.join(' '))}</p>`);
  }
  return htmlBlocks.join('\n');
}
