import { getDictionary } from "@/lib/i18n";
export const revalidate = false;

export default async function About({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  const dict = await getDictionary(locale);
  return (
    <section className="container py-16 md:py-20 max-w-3xl">
      <h1 className="text-3xl md:text-4xl font-bold text-[color:var(--brand-navy)]">
        {dict.about.title}
      </h1>
      <p className="mt-4 text-neutral-700 leading-7">{dict.about.content}</p>

      <div className="mt-8 grid sm:grid-cols-2 gap-6">
        {["Clarity", "Quality", "Speed", "Care"].map((v) => (
          <div key={v} className="rounded-lg border p-5">
            <h3 className="font-semibold text-[color:var(--brand-navy)]">{v}</h3>
            <p className="text-sm text-neutral-600 mt-2">
              {locale === "id"
                ? "Nilai inti yang membimbing kolaborasi kami."
                : "Core values guiding our collaboration."}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
