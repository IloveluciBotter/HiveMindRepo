/**
 * Agent Permissions
 * 
 * Determines what content an agent can access based on:
 * - Agent mode (public, private, draft-assistant)
 * - Repo visibility (isPublic)
 * - User permissions (stub for now)
 */

export interface PermissionContext {
  agentMode: string; // "public" | "private" | "draft-assistant"
  repoIsPublic: boolean;
  userId?: string; // Optional: for future auth integration
  isOwner?: boolean; // Optional: for future owner check
}

/**
 * Check if agent can access unpublished/draft content
 */
export function canAccessPrivateContent(context: PermissionContext): boolean {
  // Public agents can only access published content
  if (context.agentMode === "public") {
    return false;
  }

  // Private agents can access all content (for owner/collabs)
  if (context.agentMode === "private") {
    // TODO: Add actual owner/collab check
    return context.isOwner ?? false;
  }

  // Draft-assistant mode can access drafts (for owner)
  if (context.agentMode === "draft-assistant") {
    // TODO: Add actual owner check
    return context.isOwner ?? false;
  }

  return false;
}

/**
 * Determine if content should be filtered by published status
 */
export function shouldFilterByPublished(context: PermissionContext): boolean {
  return !canAccessPrivateContent(context);
}

