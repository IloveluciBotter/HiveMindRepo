/**
 * Agent Provider Factory
 * 
 * Creates the appropriate provider based on the modelProvider string
 * from RepoAgentConfig.
 */

import { StubAgentProvider } from "./stub";
import { HiveMindAgentProvider } from "./hivemind";
import type { AgentProvider } from "./types";

export function createAgentProvider(modelProvider: string): AgentProvider {
  switch (modelProvider) {
    case "stub":
    case "random_llm": // legacy default
      return new StubAgentProvider();
    
    case "hivemind":
      return new HiveMindAgentProvider();
    
    default:
      // Default to stub for unknown providers
      return new StubAgentProvider();
  }
}

export { StubAgentProvider, HiveMindAgentProvider };
export type { AgentProvider, GenerateResponseArgs, GenerateResponseResult } from "./types";

