import Link from "next/link";
import Image from "next/image";
import { getLocalizedOffers } from "@/lib/content";
import { getDictionary } from "@/lib/i18n";

export const revalidate = false;

export default async function OffersPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  await getDictionary(locale);
  const offers = getLocalizedOffers();
  const heading = locale === "id" ? "Jasa" : "Offers";
  return (
    <section className="container py-16 md:py-20">
      <h1 className="text-3xl md:text-4xl font-bold text-[color:var(--brand-navy)]">{heading}</h1>
      <div className="mt-8 grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {offers.map((offer) => {
          const slug = offer.slug[locale as 'en' | 'id'];
          const title = offer.title[locale as 'en' | 'id'];
          const desc = offer.description[locale as 'en' | 'id'];
          const thumb = offer.thumbnails?.[0] || "/vercel.svg";
          const full = offer.images?.[0] || thumb;
          return (
            <Link key={slug} href={`/${locale}/offers/${slug}`} className="group block rounded-lg border overflow-hidden">
              <div className="relative aspect-[4/3] bg-neutral-50">
                <Image
                  src={thumb}
                  alt={`${title} thumbnail`}
                  fill
                  sizes="(min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw"
                  className="object-cover transition-opacity duration-200 opacity-100 group-hover:opacity-0"
                />
                <Image
                  src={full}
                  alt={`${title} preview`}
                  fill
                  sizes="(min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw"
                  className="object-cover transition-opacity duration-200 opacity-0 group-hover:opacity-100"
                />
              </div>
              <div className="p-4">
                <h3 className="font-semibold text-[color:var(--brand-navy)]">{title}</h3>
                {desc && (
                  <p className="text-sm text-neutral-600 mt-1 line-clamp-2">{desc}</p>
                )}
              </div>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
