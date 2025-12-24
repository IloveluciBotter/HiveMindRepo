/**
 * Minimal tests for Agent Runtime
 * 
 * These are simple integration tests to verify the core functionality.
 * Run with: npm test (when test framework is set up)
 */

import { hashContent, createChunks, extractTextContent } from "../indexing";
import { shouldFilterByPublished } from "../permissions";
import { StubAgentProvider } from "../providers/stub";

describe("Agent Runtime", () => {
  describe("Indexing", () => {
    test("hashContent generates consistent hashes", () => {
      const content = "Hello, world!";
      const hash1 = hashContent(content);
      const hash2 = hashContent(content);
      
      expect(hash1).toBe(hash2);
      expect(hash1).toHaveLength(64); // SHA-256 hex string
    });

    test("extractTextContent normalizes whitespace", () => {
      const input = "Hello   world\n\nTest";
      const output = extractTextContent(input);
      
      expect(output).toBe("Hello world Test");
    });

    test("createChunks splits large content", () => {
      const longContent = "Sentence one. Sentence two. Sentence three.";
      const chunks = createChunks(longContent, "test.txt", 20);
      
      expect(chunks.length).toBeGreaterThan(1);
      expect(chunks[0].contentHash).toBeDefined();
      expect(chunks[0].filePath).toBe("test.txt");
    });
  });

  describe("Permissions", () => {
    test("public agent filters by published", () => {
      const result = shouldFilterByPublished({
        agentMode: "public",
        repoIsPublic: true,
      });
      
      expect(result).toBe(true);
    });

    test("private agent does not filter (when owner)", () => {
      const result = shouldFilterByPublished({
        agentMode: "private",
        repoIsPublic: true,
        isOwner: true,
      });
      
      expect(result).toBe(false);
    });
  });

  describe("Stub Provider", () => {
    test("generates deterministic responses", async () => {
      const provider = new StubAgentProvider();
      
      const response = await provider.generateResponse({
        systemPrompt: "",
        messages: [
          { role: "user", content: "What is this?" },
        ],
        contextChunks: [],
        repoMetadata: {
          ownerHandle: "test",
          repoName: "test-repo",
          description: "A test repo",
        },
      });
      
      expect(response.content).toContain("test/test-repo");
      expect(response.citations).toBeInstanceOf(Array);
    });

    test("includes context chunks in response", async () => {
      const provider = new StubAgentProvider();
      
      const response = await provider.generateResponse({
        systemPrompt: "",
        messages: [
          { role: "user", content: "Show me context" },
        ],
        contextChunks: [
          {
            content: "This is test content",
            contentHash: "abc123",
            filePath: "test.md",
          },
        ],
        repoMetadata: {
          ownerHandle: "test",
          repoName: "test-repo",
          description: "",
        },
      });
      
      expect(response.content).toContain("relevant content chunk");
      expect(response.citations).toContain("abc123");
    });
  });
});

