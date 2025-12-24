import { NextResponse } from "next/server";
import { z } from "zod";
import prisma from "@/lib/prisma";
import { createAgentProvider } from "@/lib/agent/providers";
import { retrieveContext } from "@/lib/agent/rag";
import { shouldFilterByPublished } from "@/lib/agent/permissions";

const ChatSchema = z.object({
  message: z.string().min(1).max(4000),
  threadId: z.string().optional(),
});

export async function POST(
  req: Request,
  { params }: { params: Promise<{ repoId: string }> }
) {
  const { repoId } = await params;
  const body = await req.json().catch(() => null);
  const parsed = ChatSchema.safeParse(body);

  if (!parsed.success) {
    return NextResponse.json(
      { error: "Invalid input", details: parsed.error.flatten() },
      { status: 400 }
    );
  }

  // Fetch repo with agent config
  const repo = await prisma.repo.findUnique({
    where: { id: repoId },
    include: { learningStatus: true, agentConfig: true },
  });

  if (!repo) {
    return NextResponse.json({ error: "Repo not found" }, { status: 404 });
  }

  if (!repo.agentConfig?.agentEnabled) {
    return NextResponse.json({ error: "Agent disabled for this repo" }, { status: 403 });
  }

  // Get or create thread
  const thread =
    parsed.data.threadId
      ? await prisma.agentThread.findFirst({
          where: { id: parsed.data.threadId, repoId: repo.id },
        })
      : null;

  const activeThread =
    thread ??
    (await prisma.agentThread.create({
      data: {
        repoId: repo.id,
        visibility: "public",
        title: `Chat with ${repo.ownerHandle}/${repo.name}`,
      },
    }));

  // Save user message
  await prisma.agentMessage.create({
    data: {
      repoId: repo.id,
      threadId: activeThread.id,
      role: "user",
      content: parsed.data.message,
      citations: [],
    },
  });

  // Retrieve context chunks using RAG
  const isPublishedOnly = shouldFilterByPublished({
    agentMode: repo.agentConfig.agentMode,
    repoIsPublic: repo.isPublic,
    // TODO: Add userId and isOwner when auth is implemented
  });

  const contextChunks = await retrieveContext(
    repo.id,
    parsed.data.message,
    5, // limit
    isPublishedOnly
  );

  // Get conversation history
  const previousMessages = await prisma.agentMessage.findMany({
    where: { threadId: activeThread.id },
    orderBy: { createdAt: "asc" },
  });

  // Format messages for provider
  const messages = previousMessages.map((msg) => ({
    role: msg.role as "user" | "assistant" | "system",
    content: msg.content,
  }));

  // Create provider and generate response
  const provider = createAgentProvider(repo.agentConfig.modelProvider);
  const response = await provider.generateResponse({
    systemPrompt: repo.agentConfig.systemPrompt || "",
    messages,
    contextChunks,
    repoMetadata: {
      ownerHandle: repo.ownerHandle,
      repoName: repo.name,
      description: repo.description,
    },
  });

  // Save assistant response
  await prisma.agentMessage.create({
    data: {
      repoId: repo.id,
      threadId: activeThread.id,
      role: "assistant",
      content: response.content,
      citations: response.citations,
    },
  });

  // Return updated thread with all messages
  const allMessages = await prisma.agentMessage.findMany({
    where: { threadId: activeThread.id },
    orderBy: { createdAt: "asc" },
  });

  return NextResponse.json({
    threadId: activeThread.id,
    messages: allMessages,
  });
}

