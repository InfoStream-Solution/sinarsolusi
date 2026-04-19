import { NextRequest, NextResponse } from "next/server";
import { createSeedJob } from "@/lib/scraper-service";
import { readRequestBody } from "@/lib/http";

export async function POST(request: NextRequest) {
  const body = await readRequestBody(request);
  const domain = String(body.domain ?? "").trim();

  if (!domain) {
    return NextResponse.json(
      { error: "Domain is required." },
      { status: 400 },
    );
  }

  try {
    const payload = await createSeedJob(domain);
    return NextResponse.json(payload, { status: 201 });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : String(error) },
      { status: 502 },
    );
  }
}
