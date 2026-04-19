import { NextRequest, NextResponse } from "next/server";
import {
  getEnabledDomainSummaries,
  startDomainAction,
} from "@/lib/scraper-service";
import { readRequestBody } from "@/lib/http";

export async function GET() {
  try {
    const domains = await getEnabledDomainSummaries();
    return NextResponse.json({ domains });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : String(error) },
      { status: 502 },
    );
  }
}

export async function POST(request: NextRequest) {
  const body = await readRequestBody(request);
  const domain = String(body.domain ?? "").trim();
  const action = String(body.action ?? "").trim();

  if (!domain) {
    return NextResponse.json({ error: "Domain is required." }, { status: 400 });
  }

  if (!["seed", "extract", "import", "pipeline"].includes(action)) {
    return NextResponse.json({ error: "Unsupported action." }, { status: 400 });
  }

  try {
    const payload = await startDomainAction(
      domain,
      action as "seed" | "extract" | "import" | "pipeline",
    );
    return NextResponse.json(payload, { status: 201 });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : String(error) },
      { status: 502 },
    );
  }
}
