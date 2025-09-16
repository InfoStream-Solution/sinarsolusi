import type { Metadata } from "next";
import { getDictionary } from "@/lib/i18n";
import Link from "next/link";
import { LanguageToggle } from "./ui/LanguageToggle";

export const revalidate = false;

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await params;
  const dict = await getDictionary(locale);
  return {
    title: `${dict.brand} | ${locale === "id" ? "Beranda" : "Home"}`,
    description:
      locale === "id"
        ? "Perusahaan teknologi berbasis Indonesia."
        : "Indonesia-based technology company.",
    alternates: {
      languages: {
        en: "/en",
        id: "/id",
      },
    },
  };
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const dict = await getDictionary(locale);
  const year = 2025;
  return (
    <html lang={locale}>
      <body>
        <header className="border-b">
          <nav className="container h-16 flex items-center justify-between">
            <Link href={`/${locale}`} className="text-[18px] font-semibold text-[color:var(--brand-navy)]">
              {dict.brand}
            </Link>
            <div className="flex items-center gap-4 text-sm">
              <Link href={`/${locale}`} className="hover:underline">{dict.nav.home}</Link>
              <Link href={`/${locale}/about`} className="hover:underline">{dict.nav.about}</Link>
              <Link href={`/${locale}/contact`} className="hover:underline">{dict.nav.contact}</Link>
              <LanguageToggle locale={locale} />
            </div>
          </nav>
        </header>
        <main className="flex-1">{children}</main>
        <footer className="border-t">
          <div className="container py-6 text-sm text-neutral-600 flex items-center justify-between">
            <span>Ac {year} {dict.brand}. {dict.footer.rights}</span>
            <span className="text-[color:var(--brand-orange)] font-medium">Made in Indonesia</span>
          </div>
        </footer>
      </body>
    </html>
  );
}
