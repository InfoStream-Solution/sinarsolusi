"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/dashboard", label: "Home", exact: true },
  { href: "/dashboard/news-pipeline", label: "News Pipeline", exact: false },
  { href: "/dashboard/seed-jobs", label: "Seed jobs", exact: false },
  { href: "/dashboard", label: "Settings", disabled: true },
];

export function DashboardNav() {
  const pathname = usePathname();

  return (
    <nav className="tk-nav mt-4 space-y-1 p-2">
      {navItems.map((item) => {
        if ("disabled" in item && item.disabled) {
          return (
            <span
              key={item.label}
              className="nav-button flex items-center px-3 py-2 text-sm font-medium"
              data-disabled="true"
            >
              {item.label}
            </span>
          );
        }

        const isActive = item.exact
          ? pathname === item.href
          : pathname === item.href || pathname.startsWith(`${item.href}/`);

        return (
          <Link
            key={item.label}
            href={item.href}
            aria-current={isActive ? "page" : undefined}
            className={[
              "nav-button flex items-center px-3 py-2 text-sm font-medium transition-colors",
            ].join(" ")}
            data-active={isActive ? "true" : "false"}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
