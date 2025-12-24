-- CreateTable
CREATE TABLE "ContentChunk" (
    "id" TEXT NOT NULL,
    "repoId" TEXT NOT NULL,
    "contentHash" TEXT NOT NULL,
    "content" TEXT NOT NULL,
    "filePath" TEXT,
    "isPublished" BOOLEAN NOT NULL DEFAULT false,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "ContentChunk_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "ContentChunk_repoId_idx" ON "ContentChunk"("repoId");

-- CreateIndex
CREATE INDEX "ContentChunk_repoId_isPublished_idx" ON "ContentChunk"("repoId", "isPublished");

-- CreateIndex
CREATE UNIQUE INDEX "ContentChunk_repoId_contentHash_key" ON "ContentChunk"("repoId", "contentHash");

-- AddForeignKey
ALTER TABLE "ContentChunk" ADD CONSTRAINT "ContentChunk_repoId_fkey" FOREIGN KEY ("repoId") REFERENCES "Repo"("id") ON DELETE CASCADE ON UPDATE CASCADE;
