# Repo AI Agent Runtime

This module implements the AI agent runtime for HiveMindRepo, providing RAG (Retrieval-Augmented Generation) capabilities with provider-swappable LLM integration.

## Architecture

### Components

1. **Provider Interface** (`providers/`)
   - Swappable LLM providers (stub, HiveMind placeholder)
   - Clean interface for adding new providers (Ollama, OpenAI, etc.)

2. **Indexing Pipeline** (`indexing.ts`)
   - Simple text extraction and chunking
   - SHA-256 hashing for deduplication
   - Called when content is published

3. **RAG Context Retrieval** (`rag.ts`)
   - Keyword-based search (simple approach)
   - Can be upgraded to vector similarity search later
   - Respects published/draft content permissions

4. **Permissions** (`permissions.ts`)
   - Public agents: only published content
   - Private agents: all content (owner/collabs)
   - Draft-assistant: draft content (owner only)

## Usage

### Indexing Content

When content is published, call the indexing function:

```typescript
import { indexRepoContent } from "@/lib/agent/indexing";

await indexRepoContent(
  repoId,
  contentText,
  filePath, // optional
  isPublished // true for published content
);
```

Or use the API endpoint:

```bash
POST /api/repos/:repoId/index
{
  "content": "Your content here...",
  "filePath": "README.md",
  "isPublished": true
}
```

### Chat Endpoint

```bash
POST /api/repos/:repoId/agent/chat
{
  "message": "What is this repo about?",
  "threadId": "optional-thread-id"
}
```

The endpoint will:
1. Retrieve relevant context chunks using RAG
2. Check permissions (published vs draft content)
3. Call the configured provider (stub, HiveMind, etc.)
4. Save messages and return response

### Provider Configuration

Providers are configured via `RepoAgentConfig.modelProvider`:
- `"stub"` or `"random_llm"`: Deterministic stub responses
- `"hivemind"`: HiveMind provider (placeholder, not yet implemented)

## Database Schema

### ContentChunk

Stores indexed content chunks:

- `id`: Unique chunk ID
- `repoId`: Repository reference
- `contentHash`: SHA-256 hash for deduplication
- `content`: The actual text content
- `filePath`: Optional source file path
- `isPublished`: Whether this is from published content
- `createdAt` / `updatedAt`: Timestamps

## Future Enhancements

1. **Vector Database Integration**
   - Replace keyword search with vector similarity
   - Use embeddings for semantic search

2. **Advanced Chunking**
   - Format-specific extractors (markdown, code, etc.)
   - Overlapping chunks for better context
   - Metadata extraction

3. **HiveMind Provider**
   - Connect to global HiveMind network
   - Use global knowledge + repo context

4. **Authentication & Permissions**
   - Real owner/collab checks
   - User-scoped thread visibility

5. **Additional Providers**
   - Ollama (local LLM)
   - OpenAI
   - Anthropic Claude
   - etc.

## Testing

See `__tests__/agent.test.ts` for example usage and test cases.

