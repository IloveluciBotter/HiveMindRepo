-- CreateEnum
CREATE TYPE "RepoLearningTier" AS ENUM ('INTERACTION_ONLY', 'LEARNING_ENABLED');

-- CreateTable
CREATE TABLE "Repo" (
    "id" TEXT NOT NULL,
    "ownerHandle" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT NOT NULL DEFAULT '',
    "isPublic" BOOLEAN NOT NULL DEFAULT true,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Repo_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "RepoLearningStatus" (
    "repoId" TEXT NOT NULL,
    "learningTier" "RepoLearningTier" NOT NULL DEFAULT 'INTERACTION_ONLY',
    "stakeAmount" DECIMAL(65,30) NOT NULL DEFAULT 0,
    "stakeLockUntil" TIMESTAMP(3),
    "intelScore" DECIMAL(65,30) NOT NULL DEFAULT 0,
    "intelVerified" BOOLEAN NOT NULL DEFAULT false,
    "learningEnabledAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "RepoLearningStatus_pkey" PRIMARY KEY ("repoId")
);

-- CreateTable
CREATE TABLE "RepoAgentConfig" (
    "repoId" TEXT NOT NULL,
    "agentEnabled" BOOLEAN NOT NULL DEFAULT true,
    "agentMode" TEXT NOT NULL DEFAULT 'public',
    "modelProvider" TEXT NOT NULL DEFAULT 'random_llm',
    "systemPrompt" TEXT NOT NULL DEFAULT '',
    "toolsAllowed" JSONB NOT NULL DEFAULT '[]',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "RepoAgentConfig_pkey" PRIMARY KEY ("repoId")
);

-- CreateTable
CREATE TABLE "AgentThread" (
    "id" TEXT NOT NULL,
    "repoId" TEXT NOT NULL,
    "visibility" TEXT NOT NULL DEFAULT 'public',
    "createdBy" TEXT,
    "title" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "AgentThread_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "AgentMessage" (
    "id" TEXT NOT NULL,
    "threadId" TEXT NOT NULL,
    "repoId" TEXT NOT NULL,
    "role" TEXT NOT NULL,
    "content" TEXT NOT NULL,
    "citations" JSONB NOT NULL DEFAULT '[]',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "AgentMessage_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "Repo_ownerHandle_name_key" ON "Repo"("ownerHandle", "name");

-- CreateIndex
CREATE INDEX "AgentMessage_threadId_idx" ON "AgentMessage"("threadId");

-- CreateIndex
CREATE INDEX "AgentMessage_repoId_idx" ON "AgentMessage"("repoId");

-- AddForeignKey
ALTER TABLE "RepoLearningStatus" ADD CONSTRAINT "RepoLearningStatus_repoId_fkey" FOREIGN KEY ("repoId") REFERENCES "Repo"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "RepoAgentConfig" ADD CONSTRAINT "RepoAgentConfig_repoId_fkey" FOREIGN KEY ("repoId") REFERENCES "Repo"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "AgentThread" ADD CONSTRAINT "AgentThread_repoId_fkey" FOREIGN KEY ("repoId") REFERENCES "Repo"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "AgentMessage" ADD CONSTRAINT "AgentMessage_threadId_fkey" FOREIGN KEY ("threadId") REFERENCES "AgentThread"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "AgentMessage" ADD CONSTRAINT "AgentMessage_repoId_fkey" FOREIGN KEY ("repoId") REFERENCES "Repo"("id") ON DELETE CASCADE ON UPDATE CASCADE;
