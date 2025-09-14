"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import type { Locale } from "@/lib/i18n";

export function LanguageToggle({ locale }: { locale: Locale }) {
  const pathname = usePathname();
  const other = locale === "id" ? "en" : "id";

  // Swap the first segment (/id or /en)
  const href = pathname ? pathname.replace(/^\/(id|en)/, `/${other}`) : `/${other}`;

  return (
    <Link
      href={href}
      aria-label={`Switch language to ${other.toUpperCase()}`}
      className="rounded-full border px-3 py-1 text-xs hover:bg-neutral-50"
    >
      {locale.toUpperCase()} | <span className="text-[color:var(--brand-orange)]">{other.toUpperCase()}</span>
    </Link>
  );
}

