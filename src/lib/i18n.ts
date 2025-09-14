export type Locale = "id" | "en";

export async function getDictionary(locale: Locale) {
  switch (locale) {
    case "id":
      return (await import("@/locales/id.json")).default;
    case "en":
    default:
      return (await import("@/locales/en.json")).default;
  }
}

export const locales: Locale[] = ["id", "en"];
export const defaultLocale: Locale = "id";
