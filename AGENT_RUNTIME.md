# Repo AI Agent Runtime - Implementation Guide

## Overview

This document describes the AI Agent Runtime system for HiveMindRepo. Each repository can have an embedded AI agent that understands the repo's content and helps users interact with it.

## Features Implemented

### ✅ Database Schema
- `ContentChunk` table for storing indexed content
- Existing `RepoAgentConfig`, `AgentThread`, `AgentMessage` tables
- Migration applied successfully

### ✅ Provider Interface
- Swappable provider system (`lib/agent/providers/`)
- Stub provider with deterministic responses
- HiveMind provider placeholder for future integration
- Easy to add new providers (Ollama, OpenAI, etc.)

### ✅ Indexing Pipeline
- Simple text extraction and chunking
- SHA-256 hashing for deduplication
- API endpoint: `POST /api/repos/:repoId/index`
- Called when content is published

### ✅ RAG Context Retrieval
- Keyword-based search (simple approach)
- Respects published/draft permissions
- Can be upgraded to vector similarity search later

### ✅ Permissions System
- Public agents: only access published content
- Private agents: access all content (stub for owner/collabs)
- Draft-assistant: access drafts (stub for owner)

### ✅ Chat Endpoint
- `POST /api/repos/:repoId/agent/chat`
- Retrieves context using RAG
- Calls configured provider
- Saves messages and threads

## API Endpoints

### Chat with Agent

```bash
POST /api/repos/:repoId/agent/chat
Content-Type: application/json

{
  "message": "What is this repo about?",
  "threadId": "optional-existing-thread-id"
}
```

Response:
```json
{
  "threadId": "thread-id",
  "messages": [
    {
      "id": "msg-1",
      "role": "user",
      "content": "What is this repo about?",
      "citations": [],
      "createdAt": "2024-12-24T..."
    },
    {
      "id": "msg-2",
      "role": "assistant",
      "content": "I'm the Repo Agent for...",
      "citations": ["chunk-hash-1"],
      "createdAt": "2024-12-24T..."
    }
  ]
}
```

### Index Content

```bash
POST /api/repos/:repoId/index
Content-Type: application/json

{
  "content": "Your content here...",
  "filePath": "README.md",
  "isPublished": true
}
```

Response:
```json
{
  "success": true,
  "message": "Content indexed successfully"
}
```

## Usage Example

### 1. Index Content When Publishing

```typescript
import { indexRepoContent } from "@/lib/agent/indexing";

// When user publishes content
await indexRepoContent(
  repoId,
  readmeContent,
  "README.md",
  true // isPublished
);
```

### 2. Chat with Agent

```typescript
const response = await fetch(`/api/repos/${repoId}/agent/chat`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    message: "What files are in this repo?",
    threadId: existingThreadId, // optional
  }),
});

const { threadId, messages } = await response.json();
```

## Configuration

Agent configuration is stored in `RepoAgentConfig`:

- `agentEnabled`: Enable/disable agent
- `agentMode`: `"public"` | `"private"` | `"draft-assistant"`
- `modelProvider`: `"stub"` | `"hivemind"` | (future: `"ollama"`, etc.)
- `systemPrompt`: Custom system prompt
- `toolsAllowed`: JSON array of allowed tools (future)

## Architecture Decisions

### Simple First, Upgrade Later

- **Chunking**: Simple sentence-based splitting (can add overlap, format-specific later)
- **Search**: Keyword matching (can add vector similarity later)
- **Permissions**: Stub checks (can add real auth later)

### Provider Swappability

The provider interface allows swapping LLM providers without changing:
- The chat endpoint
- The RAG system
- The database schema
- The UI components

### Vector DB Stub

Vector database integration is stubbed for now. The `ContentChunk` table stores:
- Text content (for keyword search)
- Content hash (for deduplication)
- Metadata (filePath, isPublished)

When vector DB is added, we can:
1. Generate embeddings on index
2. Store in vector DB
3. Update `retrieveContext()` to use vector similarity

## Testing

See `lib/agent/__tests__/agent.test.ts` for test examples.

To run tests (when test framework is configured):
```bash
npm test
```

## Future Work

1. **Vector Database Integration**
   - Add embeddings generation
   - Store in vector DB (Pinecone, Weaviate, etc.)
   - Update RAG to use vector similarity

2. **HiveMind Provider**
   - Implement actual HiveMind network connection
   - Use global knowledge + repo context

3. **Additional Providers**
   - Ollama (local LLM)
   - OpenAI GPT
   - Anthropic Claude

4. **Advanced Features**
   - Code-specific chunking
   - Markdown parsing
   - Image OCR
   - Multi-modal support

5. **Authentication**
   - Real owner/collab checks
   - User-scoped permissions
   - Thread visibility controls

## Files Created/Modified

### New Files
- `lib/agent/providers/types.ts` - Provider interface
- `lib/agent/providers/stub.ts` - Stub provider implementation
- `lib/agent/providers/hivemind.ts` - HiveMind placeholder
- `lib/agent/providers/index.ts` - Provider factory
- `lib/agent/indexing.ts` - Content indexing pipeline
- `lib/agent/rag.ts` - RAG context retrieval
- `lib/agent/permissions.ts` - Permission checks
- `app/api/repos/[repoId]/agent/chat/route.ts` - Chat endpoint
- `app/api/repos/[repoId]/index/route.ts` - Indexing endpoint
- `lib/agent/README.md` - Module documentation
- `lib/agent/__tests__/agent.test.ts` - Test examples
- `AGENT_RUNTIME.md` - This file

### Modified Files
- `prisma/schema.prisma` - Added ContentChunk model
- `prisma/migrations/.../migration.sql` - Added ContentChunk table

## Notes

- The endpoint path is `/api/repos/:repoId/agent/chat` (note: `repos` plural)
- There's also an existing endpoint at `/api/repo/:repoId/agent/chat` (singular) - this can be deprecated or kept for backward compatibility
- All provider implementations are async to support future network calls
- Citations reference `contentHash` for linking back to source chunks

