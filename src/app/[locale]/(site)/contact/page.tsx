import { getDictionary } from "@/lib/i18n";

export default async function Contact({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  const dict = await getDictionary(locale);
  return (
    <section className="container py-16 md:py-20 max-w-2xl">
      <h1 className="text-3xl md:text-4xl font-bold text-[color:var(--brand-navy)]">
        {dict.contact.title}
      </h1>
      <p className="mt-2 text-neutral-700">{dict.contact.subtitle}</p>

      <form className="mt-8 grid gap-4">
        <div>
          <label className="block text-sm mb-1">{dict.contact.name}</label>
          <input className="w-full rounded-md border px-3 py-2" placeholder="Jane Doe" />
        </div>
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm mb-1">{dict.contact.email}</label>
            <input className="w-full rounded-md border px-3 py-2" type="email" placeholder="jane@example.com" />
          </div>
          <div>
            <label className="block text-sm mb-1">{dict.contact.phone}</label>
            <input className="w-full rounded-md border px-3 py-2" placeholder="+62…" />
          </div>
        </div>
        <div>
          <label className="block text-sm mb-1">{dict.contact.message}</label>
          <textarea className="w-full rounded-md border px-3 py-2 min-h-32" placeholder={locale === "id" ? "Ceritakan kebutuhan Anda…" : "Tell us about your needs…"} />
        </div>
        <div className="flex gap-3">
          <button className="btn btn-primary" type="button">{dict.contact.send}</button>
          <a
            className="btn btn-secondary"
            href="https://wa.me/6281234567890"
            target="_blank"
            rel="noopener noreferrer"
          >
            {dict.contact.whatsapp}
          </a>
        </div>
      </form>
    </section>
  );
}
