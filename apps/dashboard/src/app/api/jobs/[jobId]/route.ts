import { NextRequest, NextResponse } from "next/server";
import { getSeedJob } from "@/lib/scraper-service";

interface RouteContext {
  params: Promise<{ jobId: string }>;
}

export async function GET(_request: NextRequest, { params }: RouteContext) {
  const { jobId } = await params;
  const parsedJobId = Number.parseInt(jobId, 10);

  if (!Number.isFinite(parsedJobId)) {
    return NextResponse.json({ error: "Invalid job id." }, { status: 400 });
  }

  try {
    const payload = await getSeedJob(parsedJobId);
    return NextResponse.json(payload);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : String(error) },
      { status: 502 },
    );
  }
}
