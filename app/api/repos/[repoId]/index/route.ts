import { NextResponse } from "next/server";
import { z } from "zod";
import prisma from "@/lib/prisma";
import { indexRepoContent } from "@/lib/agent/indexing";

const IndexSchema = z.object({
  content: z.string().min(1),
  filePath: z.string().optional(),
  isPublished: z.boolean().optional().default(true),
});

/**
 * POST /api/repos/:repoId/index
 * 
 * Index content for a repo. Called when content is published.
 * This is a simple endpoint for testing. In production, this would
 * be called automatically when content is published.
 */
export async function POST(
  req: Request,
  { params }: { params: Promise<{ repoId: string }> }
) {
  const { repoId } = await params;
  const body = await req.json().catch(() => null);
  const parsed = IndexSchema.safeParse(body);

  if (!parsed.success) {
    return NextResponse.json(
      { error: "Invalid input", details: parsed.error.flatten() },
      { status: 400 }
    );
  }

  const repo = await prisma.repo.findUnique({
    where: { id: repoId },
  });

  if (!repo) {
    return NextResponse.json({ error: "Repo not found" }, { status: 404 });
  }

  try {
    await indexRepoContent(
      repoId,
      parsed.data.content,
      parsed.data.filePath,
      parsed.data.isPublished
    );

    return NextResponse.json({
      success: true,
      message: "Content indexed successfully",
    });
  } catch (error) {
    console.error("Indexing error:", error);
    return NextResponse.json(
      { error: "Failed to index content" },
      { status: 500 }
    );
  }
}

