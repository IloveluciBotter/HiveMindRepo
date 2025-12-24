/**
 * RAG (Retrieval-Augmented Generation) Context Retrieval
 * 
 * Retrieves relevant content chunks from the repo based on the query.
 * For now, uses simple text matching. Vector search can be added later.
 */

import prisma from "@/lib/prisma";

export interface ContextChunk {
  content: string;
  filePath?: string;
  contentHash: string;
}

/**
 * Retrieve relevant context chunks for a query
 * 
 * @param repoId - The repository ID
 * @param query - The user's query/message
 * @param limit - Maximum number of chunks to return
 * @param isPublishedOnly - If true, only return published content (for public agents)
 */
export async function retrieveContext(
  repoId: string,
  query: string,
  limit: number = 5,
  isPublishedOnly: boolean = true
): Promise<ContextChunk[]> {
  // Simple keyword-based retrieval
  // TODO: Replace with vector similarity search when vector DB is integrated
  const keywords = query
    .toLowerCase()
    .split(/\s+/)
    .filter((word) => word.length > 2);

  if (keywords.length === 0) {
    // If no keywords, return most recent chunks
    const chunks = await prisma.contentChunk.findMany({
      where: {
        repoId,
        ...(isPublishedOnly ? { isPublished: true } : {}),
      },
      orderBy: { createdAt: "desc" },
      take: limit,
    });

    return chunks.map((chunk) => ({
      content: chunk.content,
      filePath: chunk.filePath || undefined,
      contentHash: chunk.contentHash,
    }));
  }

  // Search for chunks containing keywords
  // Using Prisma's text search (simple approach)
  const allChunks = await prisma.contentChunk.findMany({
    where: {
      repoId,
      ...(isPublishedOnly ? { isPublished: true } : {}),
    },
  });

  // Score chunks by keyword matches
  const scored = allChunks.map((chunk) => {
    const contentLower = chunk.content.toLowerCase();
    let score = 0;
    for (const keyword of keywords) {
      if (contentLower.includes(keyword)) {
        score += 1;
      }
    }
    return { chunk, score };
  });

  // Sort by score and return top results
  const topChunks = scored
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
    .map((item) => ({
      content: item.chunk.content,
      filePath: item.chunk.filePath || undefined,
      contentHash: item.chunk.contentHash,
    }));

  // If no matches, return recent chunks as fallback
  if (topChunks.length === 0) {
    const recentChunks = await prisma.contentChunk.findMany({
      where: {
        repoId,
        ...(isPublishedOnly ? { isPublished: true } : {}),
      },
      orderBy: { createdAt: "desc" },
      take: limit,
    });

    return recentChunks.map((chunk) => ({
      content: chunk.content,
      filePath: chunk.filePath || undefined,
      contentHash: chunk.contentHash,
    }));
  }

  return topChunks;
}

