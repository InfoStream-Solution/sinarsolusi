import type { Metadata } from "next";
import { getDictionary, locales, type Locale } from "@/lib/i18n";
import Link from "next/link";
import { LanguageToggle } from "./ui/LanguageToggle";

export async function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

type Props = {
  children: React.ReactNode;
  params: { locale: Locale };
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const dict = await getDictionary(params.locale);
  return {
    title: `${dict.brand} | ${params.locale === "id" ? "Beranda" : "Home"}`,
    description:
      params.locale === "id"
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

export default async function LocaleLayout({ children, params }: Props) {
  const dict = await getDictionary(params.locale);
  return (
    <>
      <header className="border-b">
        <nav className="container h-16 flex items-center justify-between">
          <Link href={`/${params.locale}`} className="text-[18px] font-semibold text-[color:var(--brand-navy)]">
            {dict.brand}
          </Link>
          <div className="flex items-center gap-4 text-sm">
            <Link href={`/${params.locale}`} className="hover:underline">{dict.nav.home}</Link>
            <Link href={`/${params.locale}/about`} className="hover:underline">{dict.nav.about}</Link>
            <Link href={`/${params.locale}/contact`} className="hover:underline">{dict.nav.contact}</Link>
            <LanguageToggle locale={params.locale} />
          </div>
        </nav>
      </header>
      <main className="flex-1">{children}</main>
      <footer className="border-t">
        <div className="container py-6 text-sm text-neutral-600 flex items-center justify-between">
          <span>© {new Date().getFullYear()} {dict.brand}. {dict.footer.rights}</span>
          <span className="text-[color:var(--brand-orange)] font-medium">Made in Indonesia</span>
        </div>
      </footer>
    </>
  );
}
