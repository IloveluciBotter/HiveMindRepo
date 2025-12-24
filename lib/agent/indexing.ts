/**
 * Content Indexing Pipeline
 * 
 * Simple text extraction and hashing for content chunks.
 * Vector DB integration can be added later.
 */

import { createHash } from "crypto";
import prisma from "@/lib/prisma";

export interface ContentChunk {
  content: string;
  filePath?: string;
  contentHash: string;
}

/**
 * Generate a SHA-256 hash for content deduplication
 */
export function hashContent(content: string): string {
  return createHash("sha256").update(content).digest("hex");
}

/**
 * Extract text content from various formats
 * For now, this is a simple pass-through. Later we can add:
 * - Markdown parsing
 * - Code file parsing
 * - Image OCR
 * - etc.
 */
export function extractTextContent(rawContent: string, filePath?: string): string {
  // Simple text extraction - just trim and normalize whitespace
  // TODO: Add format-specific extractors (markdown, code, etc.)
  return rawContent.trim().replace(/\s+/g, " ");
}

/**
 * Create content chunks from raw content
 * Splits large content into smaller chunks (simple approach for now)
 */
export function createChunks(
  content: string,
  filePath?: string,
  maxChunkSize: number = 1000
): ContentChunk[] {
  const extracted = extractTextContent(content, filePath);
  
  // Simple chunking: split by sentences, then by size
  const sentences = extracted.split(/[.!?]\s+/).filter((s) => s.length > 0);
  const chunks: ContentChunk[] = [];
  let currentChunk = "";

  for (const sentence of sentences) {
    if (currentChunk.length + sentence.length > maxChunkSize && currentChunk.length > 0) {
      const hash = hashContent(currentChunk);
      chunks.push({
        content: currentChunk,
        filePath,
        contentHash: hash,
      });
      currentChunk = sentence;
    } else {
      currentChunk += (currentChunk ? ". " : "") + sentence;
    }
  }

  // Add remaining chunk
  if (currentChunk.length > 0) {
    const hash = hashContent(currentChunk);
    chunks.push({
      content: currentChunk,
      filePath,
      contentHash: hash,
    });
  }

  return chunks;
}

/**
 * Index content chunks for a repo
 * Called when content is published
 */
export async function indexRepoContent(
  repoId: string,
  content: string,
  filePath?: string,
  isPublished: boolean = true
): Promise<void> {
  const chunks = createChunks(content, filePath);
  
  // Upsert chunks (deduplicate by contentHash)
  for (const chunk of chunks) {
    await prisma.contentChunk.upsert({
      where: {
        repoId_contentHash: {
          repoId,
          contentHash: chunk.contentHash,
        },
      },
      create: {
        repoId,
        contentHash: chunk.contentHash,
        content: chunk.content,
        filePath: chunk.filePath,
        isPublished,
      },
      update: {
        content: chunk.content,
        filePath: chunk.filePath,
        isPublished,
        updatedAt: new Date(),
      },
    });
  }
}

