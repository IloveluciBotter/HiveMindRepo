import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import crypto from "crypto";

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());

/**
 * Health
 */
app.get("/api/health", (_req, res) => {
  res.json({ status: "ok", ts: new Date().toISOString() });
});

/**
 * Models (MVP in-memory)
 */
type Repo = {
  id: string;
  ownerHandle: string;
  name: string; // account name
  createdAt: string;
};

type Snapshot = {
  id: string;
  repoId: string;
  title: string;
  content: string;
  createdAt: string;
};

type Publish = {
  id: string;
  repoId: string;
  snapshotId: string;
  caption: string;
  createdAt: string;
};

const repos: Repo[] = [];
const snapshots: Snapshot[] = [];
const publishes: Publish[] = [];

/**
 * Repos (account = repo)
 */
app.post("/api/repos", (req, res) => {
  const { ownerHandle, name } = req.body ?? {};
  if (!ownerHandle || !name) {
    return res.status(400).json({ error: "ownerHandle and name are required" });
  }

  const repo: Repo = {
    id: crypto.randomUUID(),
    ownerHandle: String(ownerHandle),
    name: String(name),
    createdAt: new Date().toISOString(),
  };

  repos.push(repo);
  return res.status(201).json(repo);
});

app.get("/api/repos", (_req, res) => {
  res.json(repos);
});

/**
 * Snapshots
 */
app.post("/api/repos/:repoId/snapshots", (req, res) => {
  const { repoId } = req.params;
  const repo = repos.find((r) => r.id === repoId);
  if (!repo) return res.status(404).json({ error: "repo not found" });

  const { title, content } = req.body ?? {};
  if (!title || !content) {
    return res.status(400).json({ error: "title and content are required" });
  }

  const snap: Snapshot = {
    id: crypto.randomUUID(),
    repoId,
    title: String(title),
    content: String(content),
    createdAt: new Date().toISOString(),
  };

  snapshots.push(snap);
  return res.status(201).json(snap);
});

app.get("/api/repos/:repoId/snapshots", (req, res) => {
  const { repoId } = req.params;
  res.json(snapshots.filter((s) => s.repoId === repoId));
});

/**
 * Publish snapshot to feed
 */
app.post("/api/repos/:repoId/publish", (req, res) => {
  const { repoId } = req.params;
  const repo = repos.find((r) => r.id === repoId);
  if (!repo) return res.status(404).json({ error: "repo not found" });

  const { snapshotId, caption } = req.body ?? {};
  if (!snapshotId) return res.status(400).json({ error: "snapshotId is required" });

  const snap = snapshots.find((s) => s.id === snapshotId && s.repoId === repoId);
  if (!snap) return res.status(404).json({ error: "snapshot not found for repo" });

  const pub: Publish = {
    id: crypto.randomUUID(),
    repoId,
    snapshotId: String(snapshotId),
    caption: caption ? String(caption) : "",
    createdAt: new Date().toISOString(),
  };

  publishes.push(pub);
  return res.status(201).json(pub);
});

/**
 * Feed (latest publishes first)
 */
app.get("/api/feed", (_req, res) => {
  const feed = publishes
    .slice()
    .sort((a, b) => (a.createdAt < b.createdAt ? 1 : -1))
    .map((p) => {
      const repo = repos.find((r) => r.id === p.repoId);
      const snap = snapshots.find((s) => s.id === p.snapshotId);
      return {
        ...p,
        repo: repo ? { id: repo.id, ownerHandle: repo.ownerHandle, name: repo.name } : null,
        snapshot: snap ? { id: snap.id, title: snap.title, content: snap.content } : null,
      };
    });

  res.json(feed);
});

/**
 * Profile (timeline for a handle)
 */
app.get("/api/profile/:handle", (req, res) => {
  const { handle } = req.params;

  const myRepos = repos.filter((r) => r.ownerHandle === handle);
  const myRepoIds = new Set(myRepos.map((r) => r.id));

  const timeline = publishes
    .filter((p) => myRepoIds.has(p.repoId))
    .slice()
    .sort((a, b) => (a.createdAt < b.createdAt ? 1 : -1))
    .map((p) => {
      const repo = repos.find((r) => r.id === p.repoId);
      const snap = snapshots.find((s) => s.id === p.snapshotId);
      return {
        ...p,
        repo: repo ? { id: repo.id, ownerHandle: repo.ownerHandle, name: repo.name } : null,
        snapshot: snap ? { id: snap.id, title: snap.title, content: snap.content } : null,
      };
    });

  res.json({ handle, repos: myRepos, timeline });
});

const port = Number(process.env.PORT || 5050);
app.listen(port, () => {
  console.log(`API listening on http://localhost:${port}`);
});
