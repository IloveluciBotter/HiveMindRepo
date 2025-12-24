/**
 * Stub Agent Provider
 * 
 * Returns deterministic responses for testing and development.
 * This will be replaced with real LLM providers later.
 */

import type { AgentProvider, GenerateResponseArgs, GenerateResponseResult } from "./types";

export class StubAgentProvider implements AgentProvider {
  async generateResponse(args: GenerateResponseArgs): Promise<GenerateResponseResult> {
    const { messages, contextChunks, repoMetadata, systemPrompt } = args;
    const lastUserMessage = messages
      .filter((m) => m.role === "user")
      .slice(-1)[0]?.content || "";

    const lower = lastUserMessage.toLowerCase();
    const citations: string[] = [];

    // If we have context chunks, reference them
    if (contextChunks.length > 0) {
      citations.push(contextChunks[0].contentHash);
    }

    // Deterministic responses based on keywords
    if (lower.includes("what is this") || lower.includes("explain")) {
      return {
        content: `I'm the Repo Agent for ${repoMetadata.ownerHandle}/${repoMetadata.repoName}.\n\nDescription: ${
          repoMetadata.description || "(no description yet)"
        }\n\n${contextChunks.length > 0 ? `I found ${contextChunks.length} relevant content chunks in this repo.` : ""}\n\nAsk me about the roadmap, changes, or how to contribute.`,
        citations,
      };
    }

    if (lower.includes("context") || lower.includes("content") || lower.includes("chunk")) {
      if (contextChunks.length > 0) {
        const chunkPreview = contextChunks[0].content.substring(0, 200);
        return {
          content: `I found ${contextChunks.length} relevant content chunk(s). Here's a preview:\n\n"${chunkPreview}..."\n\n${contextChunks[0].filePath ? `(from ${contextChunks[0].filePath})` : ""}`,
          citations,
        };
      }
      return {
        content: "I don't have any indexed content for this repo yet. Content will be indexed when you publish.",
        citations: [],
      };
    }

    if (lower.includes("learning") || lower.includes("hivemind")) {
      return {
        content: `This repo's agent is currently using a **stub provider**.\n\n- Current provider: Stub (deterministic responses)\n- Future: Will support HiveMind provider integration\n\nThe agent can access published content chunks for context.`,
        citations,
      };
    }

    // Default response
    return {
      content: `Got it. You said:\n"${lastUserMessage}"\n\nRight now I'm a stubbed agent with RAG support. I can search through indexed content chunks from this repo. Next we'll connect me to a real model provider (and later swap to HiveMind) without changing the UI or API.`,
      citations,
    };
  }
}

