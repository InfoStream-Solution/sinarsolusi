"use client";
import Image from "next/image";
import { useRef, useState, useEffect, KeyboardEvent } from "react";

type Item = { thumb: string; full: string; alt: string };

export function GalleryMedia({
  items,
  layout = "carousel",
  hoverSwap = true,
  aspect = "4/3",
}: {
  items: Item[];
  layout?: "carousel" | "grid";
  hoverSwap?: boolean;
  aspect?: "4/3" | "1/1" | "16/9";
}) {
  if (!items?.length) return null;
  if (layout === "grid") {
    return (
      <div className="mt-8 grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {items.map((it, i) => (
          <Tile key={i} item={it} hoverSwap={hoverSwap} aspect={aspect} />
        ))}
      </div>
    );
  }
  return <Carousel items={items} hoverSwap={hoverSwap} aspect={aspect} />;
}

function aspectClass(a: "4/3" | "1/1" | "16/9") {
  switch (a) {
    case "1/1":
      return "aspect-square";
    case "16/9":
      return "aspect-video";
    default:
      return "aspect-[4/3]";
  }
}

function Tile({ item, hoverSwap, aspect }: { item: Item; hoverSwap: boolean; aspect: "4/3"|"1/1"|"16/9" }) {
  const a = aspectClass(aspect);
  return (
    <div className={`group relative ${a} rounded-lg overflow-hidden border bg-neutral-50`}>
      <Image
        src={item.thumb}
        alt={`${item.alt} thumbnail`}
        fill
        sizes="(min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw"
        className={`object-cover transition-opacity duration-200 ${hoverSwap ? "opacity-100 group-hover:opacity-0" : "opacity-100"}`}
      />
      <Image
        src={item.full}
        alt={`${item.alt} full`}
        fill
        sizes="(min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw"
        className={`object-cover transition-opacity duration-200 ${hoverSwap ? "opacity-0 group-hover:opacity-100" : "hidden"}`}
      />
    </div>
  );
}

function Carousel({ items, hoverSwap, aspect }: { items: Item[]; hoverSwap: boolean; aspect: "4/3"|"1/1"|"16/9" }) {
  const a = aspectClass(aspect);
  const ref = useRef<HTMLDivElement>(null);
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const handler = () => {
      const children = Array.from(el.children) as HTMLElement[];
      const mid = el.scrollLeft + el.clientWidth / 2;
      let i = 0, bestDelta = Infinity;
      children.forEach((ch, idx) => {
        const rect = ch.getBoundingClientRect();
        const left = el.scrollLeft + ch.offsetLeft + rect.width / 2;
        const delta = Math.abs(left - mid);
        if (delta < bestDelta) { bestDelta = delta; i = idx; }
      });
      setIndex(i);
    };
    el.addEventListener('scroll', handler, { passive: true });
    handler();
    return () => el.removeEventListener('scroll', handler as EventListener);
  }, []);

  const scrollTo = (i: number) => {
    const el = ref.current;
    if (!el) return;
    const child = el.children[i] as HTMLElement | undefined;
    if (!child) return;
    el.scrollTo({ left: child.offsetLeft, behavior: 'smooth' });
  };

  const onKey = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'ArrowRight') { e.preventDefault(); next(); }
    if (e.key === 'ArrowLeft') { e.preventDefault(); prev(); }
  };
  const prev = () => scrollTo(Math.max(0, index - 1));
  const next = () => scrollTo(Math.min(items.length - 1, index + 1));

  return (
    <div className="mt-8">
      <div
        ref={ref}
        className="flex gap-4 overflow-x-auto scroll-smooth snap-x snap-mandatory focus:outline-none"
        tabIndex={0}
        onKeyDown={onKey}
        aria-roledescription="carousel"
        aria-label="Gallery"
      >
        {items.map((it, i) => (
          <div key={i} className={`shrink-0 w-[85%] sm:w-[60%] lg:w-[40%] snap-center`} aria-roledescription="slide" aria-label={`${i+1} of ${items.length}`}>
            <Tile item={it} hoverSwap={hoverSwap} aspect={aspect} />
          </div>
        ))}
      </div>
      <div className="mt-4 flex items-center justify-center gap-2">
        <button className="btn btn-secondary px-3 py-1 text-sm" onClick={prev} aria-label="Previous" disabled={index === 0}>Prev</button>
        <div className="text-sm text-neutral-600">{index + 1} / {items.length}</div>
        <button className="btn btn-secondary px-3 py-1 text-sm" onClick={next} aria-label="Next" disabled={index === items.length - 1}>Next</button>
      </div>
    </div>
  );
}
