/**
 * Agent Provider Interface
 * 
 * This interface allows swapping between different LLM providers
 * (local stub, Ollama, OpenAI, HiveMind, etc.) without changing
 * the chat endpoint implementation.
 */

export interface AgentProvider {
  /**
   * Generate a response given the context and messages
   */
  generateResponse(args: GenerateResponseArgs): Promise<GenerateResponseResult>;
}

export interface GenerateResponseArgs {
  /**
   * System prompt for the agent
   */
  systemPrompt: string;
  
  /**
   * Conversation history (user and assistant messages)
   */
  messages: Array<{
    role: "user" | "assistant" | "system";
    content: string;
  }>;
  
  /**
   * Retrieved context chunks from RAG
   */
  contextChunks: Array<{
    content: string;
    filePath?: string;
    contentHash: string;
  }>;
  
  /**
   * Repo metadata for context
   */
  repoMetadata: {
    ownerHandle: string;
    repoName: string;
    description: string;
  };
}

export interface GenerateResponseResult {
  /**
   * The generated response text
   */
  content: string;
  
  /**
   * Citations to the context chunks used (contentHash references)
   */
  citations: string[];
}

