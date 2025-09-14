import { getDictionary } from "@/lib/i18n";
import Image from "next/image";
import Link from "next/link";

export const runtime = "edge";

export default async function Home({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  const dict = await getDictionary(locale);
  return (
    <section>
      {/* Hero with navy background */}
      <div className="on-dark bg-[color:var(--brand-navy)] text-white">
        <div className="container py-16 md:py-24">
          <div className="grid md:grid-cols-2 gap-8 md:gap-12 items-center">
            <div>
              <h1 className="text-3xl md:text-5xl font-bold tracking-tight">
                {dict.hero.title}
              </h1>
              <p className="mt-4 text-white/80 text-base md:text-lg">
                {dict.hero.subtitle}
              </p>
              <div className="mt-8 flex gap-4">
                <Link href={`/${locale}/contact`} className="btn btn-primary">
                  {dict.hero.cta}
                </Link>
                <Link href={`/${locale}/about`} className="btn btn-secondary">
                  {locale === "id" ? "Pelajari Lebih Lanjut" : "Learn More"}
                </Link>
              </div>
            </div>
            <div className="relative aspect-[4/3] w-full rounded-xl overflow-hidden shadow-sm ring-1 ring-white/10 bg-white/5">
              <Image src="/globe.svg" alt="Sinar Solusi" fill className="p-10 object-contain invert" />
            </div>
          </div>
        </div>
      </div>

      {/* Value props on light background */}
      <div className="container py-16 md:py-20">
        <div className="grid sm:grid-cols-3 gap-6">
          {["Strategy", "Engineering", "Delivery"].map((k, i) => (
            <div key={i} className="rounded-lg border p-6">
              <h3 className="font-semibold text-[color:var(--brand-navy)]">{k}</h3>
              <p className="text-sm text-neutral-600 mt-2">
                {locale === "id"
                  ? "Fokus pada prioritas, kualitas rekayasa, dan pengiriman yang konsisten."
                  : "Focus on priorities, engineering quality, and consistent delivery."}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
