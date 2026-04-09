export type Locale = "id" | "en";

export async function getDictionary(locale: string) {
  const normalized: Locale = locale === "id" ? "id" : "en";
  switch (normalized) {
    case "id":
      return (await import("@/locales/id.json")).default;
    case "en":
    default:
      return (await import("@/locales/en.json")).default;
  }
}

export const locales: Locale[] = ["id", "en"];
export const defaultLocale: Locale = "id";
