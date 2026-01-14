#!/usr/bin/env node
/**
 * Generate a JSON report describing GitHub workflows/actions using AI.
 * Supports z.ai (OpenAI-compatible) and Anthropic Claude.
 *
 * Can scan a single repository or entire organization.
 *
 * CACHING:
 * This script uses file hashing to cache AI descriptions and avoid redundant API calls.
 * Cache files are stored in .ai-cache/ directory. To enable GitHub Actions caching,
 * add cache steps before and after this script using actions/cache@v4 with path: .ai-cache
 * and a unique key based on hashFiles of your YAML files.
 *
 * Output JSON structure:
 * {
 *   "organization": string,
 *   "repository": string,
 *   "actions": [
 *     {
 *       "name": string,
 *       "filename": string,
 *       "category": string,
 *       "description": string (AI),
 *       "execution_method": string,
 *       "status_link": string,
 *       "script_link": string,
 *       "filelength": number (file size in bytes),
 *       "edited": string (ISO 8601 timestamp of last file modification),
 *       "executed": string (ISO 8601 timestamp of last workflow run),
 *       "last_run_status": string ("success", "failure", etc.),
 *       "retry_count": number (number of re-run attempts on last workflow),
 *       "total_run_time_seconds": number (total execution time including retries),
 *       "last_run_duration_seconds": number (duration of last run attempt),
 *       "total_runs": number (total number of runs recorded)
 *     }
 *   ]
 * }
 *
 * Env:
 * - ZAI_API_KEY (optional, for z.ai)
 * - ANTHROPIC_API_KEY (optional, for Anthropic Claude)
 * - AI_MODEL (optional, default: glm-4.7 for z.ai, claude-sonnet-4-5 for Anthropic)
 * - AI_PROVIDER (optional, "zai", "anthropic", or "openai", default: "openai")
 * - SCAN_ROOT (optional, default: .github)
 * - REPO_DEFAULT_BRANCH (optional, default: main)
 * - ORGANIZATION (optional, scan all repos in this organization)
 * - GITHUB_REPOSITORY (auto-set in Actions, format: owner/repo)
 * - GITHUB_TOKEN (required for organization scanning)
 */

import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import fg from "fast-glob";
import yaml from "js-yaml";
import crypto from "node:crypto";

// Retry with exponential backoff for rate limiting
async function fetchWithRetry(fetchFn, maxRetries = 5) {
  // Rate limit: 15 requests per 60 seconds = 4 seconds minimum between requests
  const MIN_WAIT_MS = 4000;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fetchFn();
    } catch (error) {
      if (attempt === maxRetries - 1) throw error;

      // Check if it's a rate limit error (429)
      if (error.message.includes("429") || error.message.includes("RateLimitReached")) {
        // Exponential backoff starting at minimum wait time: 4s, 8s, 16s, 32s, 64s
        const waitTime = Math.max(MIN_WAIT_MS, Math.pow(2, attempt) * MIN_WAIT_MS);
        console.log(`Rate limit hit, retry ${attempt + 1}/${maxRetries} after ${waitTime / 1000}s...`);
        await new Promise(resolve => setTimeout(resolve, waitTime));
      } else {
        throw error; // Re-throw non-rate-limit errors immediately
      }
    }
  }
}

const ZAI_API_URL = "https://api.z.ai/api/paas/v4/chat/completions";
const ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages";
const OPENAI_API_URL = "https://models.inference.ai.azure.com/chat/completions";

// Cache configuration
const CACHE_DIR = ".ai-cache";
const CACHE_VERSION = "v1";

/**
 * Compute SHA-256 hash of file content
 */
function computeFileHash(content) {
  return crypto.createHash("sha256").update(content).digest("hex");
}

/**
 * Get cache file path for a given workflow file
 */
function getCachePath(relPath) {
  const safeName = relPath.replace(/[^a-zA-Z0-9._-]/g, "_");
  return path.resolve(process.cwd(), CACHE_DIR, `${safeName}.json`);
}

/**
 * Load cached AI description if available and valid
 */
async function loadCachedDescription(relPath, content) {
  const cachePath = getCachePath(relPath);

  try {
    const cacheData = JSON.parse(await fs.readFile(cachePath, "utf8"));

    // Verify cache version
    if (cacheData.version !== CACHE_VERSION) {
      console.log(`Cache version mismatch for ${relPath}, regenerating...`);
      return null;
    }

    // Verify file content hash
    const currentHash = computeFileHash(content);
    if (cacheData.content_hash !== currentHash) {
      console.log(`File changed for ${relPath}, regenerating description...`);
      return null;
    }

    // Verify AI model hasn't changed (optional, can be useful)
    const currentModel = process.env.AI_MODEL || "default";
    if (cacheData.ai_model && cacheData.ai_model !== currentModel) {
      console.log(`AI model changed for ${relPath}, regenerating...`);
      return null;
    }

    console.log(`✓ Using cached description for ${relPath}`);
    return {
      description: cacheData.description,
      execution_method: cacheData.execution_method,
    };
  } catch (error) {
    // Cache file doesn't exist or is invalid
    return null;
  }
}

/**
 * Save AI description to cache
 */
async function saveCachedDescription(relPath, content, description, execution_method) {
  const cachePath = getCachePath(relPath);

  try {
    // Ensure cache directory exists
    await fs.mkdir(path.dirname(cachePath), { recursive: true });

    const cacheData = {
      version: CACHE_VERSION,
      content_hash: computeFileHash(content),
      ai_model: process.env.AI_MODEL || "default",
      relPath,
      description,
      execution_method,
      cached_at: new Date().toISOString(),
    };

    await fs.writeFile(cachePath, JSON.stringify(cacheData, null, 2) + "\n", "utf8");
    console.log(`✓ Cached description for ${relPath} -> ${cachePath}`);
  } catch (error) {
    console.warn(`Warning: Failed to cache description for ${relPath}:`, error.message);
    // Don't fail the entire process if caching fails
  }
}

function requiredEnv(name) {
  const v = process.env[name];
  if (!v) {
    console.error(`Missing required env var: ${name}`);
    process.exit(2);
  }
  return v;
}

function getProvider() {
  const provider = process.env.AI_PROVIDER || "openai";
  if (provider !== "zai" && provider !== "anthropic" && provider !== "openai") {
    console.error(`Invalid AI_PROVIDER: ${provider}. Must be "zai", "anthropic", or "openai"`);
    process.exit(2);
  }
  return provider;
}

function safeJsonParse(maybeJsonText) {
  // Try direct parse first
  try {
    return JSON.parse(maybeJsonText);
  } catch {}

  // Try extracting the first JSON object in the text
  const firstBrace = maybeJsonText.indexOf("{");
  const lastBrace = maybeJsonText.lastIndexOf("}");
  if (firstBrace >= 0 && lastBrace > firstBrace) {
    const slice = maybeJsonText.slice(firstBrace, lastBrace + 1);
    try {
      return JSON.parse(slice);
    } catch {}
  }
  return null;
}

function isWorkflowFile(file) {
  const p = file.replaceAll("\\", "/");
  return p.includes(".github/workflows/") && (p.endsWith(".yml") || p.endsWith(".yaml"));
}

function isActionFile(file) {
  const base = path.basename(file).toLowerCase();
  return base === "action.yml" || base === "action.yaml";
}

function repoLinksForFile(relPath) {
  const server = process.env.GITHUB_SERVER_URL || "https://github.com";
  const repo = process.env.GITHUB_REPOSITORY; // e.g. owner/name
  const branch = process.env.REPO_DEFAULT_BRANCH || "main";

  if (!repo) {
    // Fallback: local only
    return {
      script_link: null,
      status_link: null,
    };
  }

  const script_link = `${server}/${repo}/blob/${branch}/${relPath.replaceAll("\\", "/")}`;

  // For workflows, status link points to Actions workflow page; else null
  const status_link = isWorkflowFile(relPath)
    ? `${server}/${repo}/actions/workflows/${path.basename(relPath)}`
    : null;

  return { script_link, status_link };
}

function summarizeExecutionMethod(relPath, doc) {
  // Best-effort parsing for workflows/actions (we still ask AI too).
  if (isWorkflowFile(relPath)) {
    const onBlock = doc?.on ?? doc?.["on"];
    if (!onBlock) return "GitHub Actions workflow (trigger unknown)";

    if (typeof onBlock === "string") return `Triggered on: ${onBlock}`;
    if (Array.isArray(onBlock)) return `Triggered on: ${onBlock.join(", ")}`;
    if (typeof onBlock === "object") return `Triggered on: ${Object.keys(onBlock).join(", ")}`;

    return "GitHub Actions workflow (trigger unknown)";
  }

  if (isActionFile(relPath)) {
    const runs = doc?.runs;
    if (!runs) return "GitHub Action (runs block unknown)";
    const using = runs?.using;
    if (using) return `Action runs using: ${using}`;
    return "GitHub Action (execution unknown)";
  }

  return "Unknown";
}

async function getFileEditTime(filePath) {
  try {
    const stats = await fs.stat(filePath);
    return stats.mtime.toISOString();
  } catch {
    return null;
  }
}

async function getWorkflowRunDetails(workflowName, apiKey) {
  const repo = process.env.GITHUB_REPOSITORY;
  const server = process.env.GITHUB_SERVER_URL || "https://github.com";
  const apiUrl = server.replace("github.com", "api.github.com");

  if (!repo || !workflowName) return null;

  try {
    // Fetch multiple recent runs to calculate statistics
    const res = await fetch(`${apiUrl}/repos/${repo}/actions/workflows/${workflowName}/runs?per_page=10`, {
      headers: {
        "authorization": `Bearer ${apiKey}`,
        "accept": "application/vnd.github.v3+json",
      },
    });

    if (!res.ok) return null;

    const data = await res.json();
    const runs = data?.workflow_runs || [];

    if (runs.length === 0) return null;

    // Get the most recent run
    const lastRun = runs[0];

    // Calculate retry count for the most recent workflow run
    // GitHub uses run_number for the workflow run and run_attempt for retries
    // run_attempt > 1 indicates this is a retry
    const retryCount = lastRun.run_attempt ? lastRun.run_attempt - 1 : 0;

    // Calculate duration for the last run attempt (in seconds)
    const lastRunDuration = lastRun.updated_at && lastRun.created_at
      ? Math.floor((new Date(lastRun.updated_at) - new Date(lastRun.created_at)) / 1000)
      : null;

    // Calculate total execution time including all retry attempts
    // Sum up all runs with the same run_number (original + retries)
    const lastRunNumber = lastRun.run_number;
    const retryRuns = runs.filter(r => r.run_number === lastRunNumber);
    const totalRunTime = retryRuns.reduce((sum, run) => {
      if (run.updated_at && run.created_at) {
        return sum + Math.floor((new Date(run.updated_at) - new Date(run.created_at)) / 1000);
      }
      return sum;
    }, 0);

    // Get total number of runs (from the fetched sample)
    // Note: GitHub API returns up to per_page runs, so this is a sample
    const totalRuns = runs.length;

    return {
      executed: lastRun?.updated_at || lastRun?.created_at || null,
      last_run_status: lastRun?.conclusion || lastRun?.status || "unknown",
      retry_count: retryCount,
      total_run_time_seconds: totalRunTime || null,
      last_run_duration_seconds: lastRunDuration,
      total_runs: totalRuns,
    };
  } catch (error) {
    console.error(`Error fetching workflow details for ${workflowName}:`, error.message);
    return null;
  }
}

async function callZai({ apiKey, model, fileKind, relPath, content, parsedExecution }) {
  const systemContent = [
    "You are a senior DevOps engineer.",
    "You will analyze a GitHub Actions workflow or action definition file.",
    "Return STRICT JSON only, no markdown, no extra text.",
    "",
    "JSON schema:",
    "{",
    '  "description": string,',
    '  "execution_method": string',
    "}",
    "",
    "Rules:",
    "- Be concise but specific (1–4 sentences for description).",
    "- For description: Focus ONLY on what the workflow/action DOES - its purpose, operations, and outcomes. DO NOT mention: triggers/events, how it's invoked, repository owner restrictions, or permissions/conditions. Focus on the actual work performed.",
    "- For execution_method: List concrete triggers/entrypoints (events, workflow_dispatch inputs, schedule cron, reusable workflow calls, composite steps, docker/js, etc.).",
    "- Do not invent URLs or file paths; only describe behavior based on content.",
  ].join("\n");

  const userContent = [
    `File kind: ${fileKind}`,
    `Path: ${relPath}`,
    `Parsed execution hint: ${parsedExecution}`,
    "",
    "File content:",
    content,
  ].join("\n");

  const body = {
    model,
    messages: [
      { role: "system", content: systemContent },
      { role: "user", content: userContent },
    ],
    temperature: 0.3,
    max_tokens: 400,
    stream: false,
  };

  const res = await fetchWithRetry(async () => {
    const response = await fetch(ZAI_API_URL, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "authorization": `Bearer ${apiKey}`,
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const text = await response.text().catch(() => "");
      throw new Error(`Z.ai API error ${response.status}: ${text}`);
    }
    return response;
  });

  const data = await res.json();

  // Z.ai (OpenAI-compatible) returns choices[0].message.content
  const text = data?.choices?.[0]?.message?.content || "";

  const json = safeJsonParse(text);
  if (!json || typeof json !== "object") {
    throw new Error(`Could not parse Z.ai JSON for ${relPath}. Raw: ${text.slice(0, 500)}`);
  }

  return {
    description: String(json.description ?? "").trim(),
    execution_method: String(json.execution_method ?? "").trim(),
  };
}

async function callOpenAI({ apiKey, model, fileKind, relPath, content, parsedExecution }) {
  const systemContent = [
    "You are a senior DevOps engineer.",
    "You will analyze a GitHub Actions workflow or action definition file.",
    "Return STRICT JSON only, no markdown, no extra text.",
    "",
    "JSON schema:",
    "{",
    '  "description": string,',
    '  "execution_method": string',
    "}",
    "",
    "Rules:",
    "- Be concise but specific (1–4 sentences for description).",
    "- For description: Focus ONLY on what the workflow/action DOES - its purpose, operations, and outcomes. DO NOT mention: triggers/events, how it's invoked, repository owner restrictions, or permissions/conditions. Focus on the actual work performed.",
    "- For execution_method: List concrete triggers/entrypoints (events, workflow_dispatch inputs, schedule cron, reusable workflow calls, composite steps, docker/js, etc.).",
    "- Do not invent URLs or file paths; only describe behavior based on content.",
  ].join("\n");

  const userContent = [
    `File kind: ${fileKind}`,
    `Path: ${relPath}`,
    `Parsed execution hint: ${parsedExecution}`,
    "",
    "File content:",
    content,
  ].join("\n");

  const body = {
    model,
    messages: [
      { role: "system", content: systemContent },
      { role: "user", content: userContent },
    ],
    temperature: 0.3,
    max_tokens: 400,
  };

  const res = await fetchWithRetry(async () => {
    const response = await fetch(OPENAI_API_URL, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "authorization": `Bearer ${apiKey}`,
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const text = await response.text().catch(() => "");
      throw new Error(`OpenAI API error ${response.status}: ${text}`);
    }
    return response;
  });

  const data = await res.json();

  // OpenAI-compatible API returns choices[0].message.content
  const text = data?.choices?.[0]?.message?.content || "";

  const json = safeJsonParse(text);
  if (!json || typeof json !== "object") {
    throw new Error(`Could not parse OpenAI JSON for ${relPath}. Raw: ${text.slice(0, 500)}`);
  }

  return {
    description: String(json.description ?? "").trim(),
    execution_method: String(json.execution_method ?? "").trim(),
  };
}

async function callAnthropic({ apiKey, model, fileKind, relPath, content, parsedExecution }) {
  const system = [
    "You are a senior DevOps engineer.",
    "You will analyze a GitHub Actions workflow or action definition file.",
    "Return STRICT JSON only, no markdown, no extra text.",
    "",
    "JSON schema:",
    "{",
    '  "description": string,',
    '  "execution_method": string',
    "}",
    "",
    "Rules:",
    "- Be concise but specific (1–4 sentences for description).",
    "- For description: Focus ONLY on what the workflow/action DOES - its purpose, operations, and outcomes. DO NOT mention: triggers/events, how it's invoked, repository owner restrictions, or permissions/conditions. Focus on the actual work performed.",
    "- For execution_method: List concrete triggers/entrypoints (events, workflow_dispatch inputs, schedule cron, reusable workflow calls, composite steps, docker/js, etc.).",
    "- Do not invent URLs or file paths; only describe behavior based on content.",
  ].join("\n");

  const user = [
    `File kind: ${fileKind}`,
    `Path: ${relPath}`,
    `Parsed execution hint: ${parsedExecution}`,
    "",
    "File content:",
    content,
  ].join("\n");

  const body = {
    model,
    max_tokens: 400,
    messages: [{ role: "user", content: user }],
    system,
  };

  const res = await fetchWithRetry(async () => {
    const response = await fetch(ANTHROPIC_API_URL, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-api-key": apiKey,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const text = await response.text().catch(() => "");
      throw new Error(`Anthropic API error ${response.status}: ${text}`);
    }
    return response;
  });

  const data = await res.json();

  // Anthropic Messages API returns content as array of blocks
  const text = Array.isArray(data?.content)
    ? data.content.map((b) => (b?.type === "text" ? b.text : "")).join("")
    : "";

  const json = safeJsonParse(text);
  if (!json || typeof json !== "object") {
    throw new Error(`Could not parse Anthropic JSON for ${relPath}. Raw: ${text.slice(0, 500)}`);
  }

  return {
    description: String(json.description ?? "").trim(),
    execution_method: String(json.execution_method ?? "").trim(),
  };
}

async function main() {
  const provider = getProvider();
  const apiKey = provider === "zai"
    ? requiredEnv("ZAI_API_KEY")
    : provider === "anthropic"
    ? requiredEnv("ANTHROPIC_API_KEY")
    : requiredEnv("GITHUB_TOKEN");

  const model = process.env.AI_MODEL || (provider === "zai" ? "glm-4.7" : provider === "anthropic" ? "claude-sonnet-4-5" : "gpt-4o-mini");
  const scanRoot = process.env.SCAN_ROOT || ".github";

  // Get repository and organization info from environment
  const githubRepository = process.env.GITHUB_REPOSITORY; // e.g. "owner/repo"
  const organization = githubRepository?.split("/")[0] || null;
  const repository = githubRepository?.split("/")[1] || null;

  const patterns = [
    `${scanRoot.replaceAll("\\", "/")}/workflows/**/*.{yml,yaml}`,
    `${scanRoot.replaceAll("\\", "/")}/**/action.{yml,yaml}`,
  ];

  const files = await fg(patterns, { dot: true, onlyFiles: true, unique: true });

  const actions = [];
  let cacheHits = 0;
  let cacheMisses = 0;

  for (const file of files) {
    const relPath = file.replaceAll("\\", "/");
    const filename = path.basename(relPath);

    const raw = await fs.readFile(file, "utf8");

    // Parse YAML best-effort
    let doc = null;
    try {
      doc = yaml.load(raw);
    } catch {
      doc = null;
    }

    // Use workflow/action name from YAML if available, otherwise fallback to filename
    const rawName = doc?.name || filename;

    // Extract category from name if it follows "Category: Description" pattern
    let category = "generic";
    let name = rawName;
    const categoryMatch = rawName.match(/^([^:]+):\s*(.+)$/);
    if (categoryMatch) {
      category = categoryMatch[1].trim();
      name = categoryMatch[2].trim();
    }

    const fileKind = isWorkflowFile(relPath)
      ? "workflow"
      : isActionFile(relPath)
      ? "action"
      : "unknown";

    const parsedExecution = summarizeExecutionMethod(relPath, doc);

    let ai;
    try {
      // Try to load from cache first
      const cached = await loadCachedDescription(relPath, raw);

      if (cached) {
        // Use cached description
        ai = cached;
        cacheHits++;
      } else {
        // Generate new description with AI
        const callAI = provider === "zai" ? callZai : provider === "anthropic" ? callAnthropic : callOpenAI;
        ai = await callAI({
          apiKey,
          model,
          fileKind,
          relPath,
          content: raw.slice(0, 20000), // avoid huge payloads
          parsedExecution,
        });

        // Save to cache for future runs
        await saveCachedDescription(relPath, raw, ai.description, ai.execution_method);
        cacheMisses++;
      }
    } catch (e) {
      ai = {
        description: `AI description failed: ${e.message}`,
        execution_method: parsedExecution,
      };
    }

    const { script_link, status_link } = repoLinksForFile(relPath);

    // Get file edit time and size
    const edited = await getFileEditTime(file);
    const stats = await fs.stat(file);
    const filelength = stats.size;

    // Get workflow execution details (only for workflows)
    let executed = null;
    let last_run_status = null;
    let retry_count = 0;
    let total_run_time_seconds = null;
    let last_run_duration_seconds = null;
    let total_runs = 0;

    if (isWorkflowFile(relPath)) {
      const runDetails = await getWorkflowRunDetails(filename, apiKey);
      if (runDetails) {
        executed = runDetails.executed;
        last_run_status = runDetails.last_run_status;
        retry_count = runDetails.retry_count;
        total_run_time_seconds = runDetails.total_run_time_seconds;
        last_run_duration_seconds = runDetails.last_run_duration_seconds;
        total_runs = runDetails.total_runs;
      }
    }

    actions.push({
      name,
      filename,
      category,
      description: ai.description || "(no description returned)",
      execution_method: ai.execution_method || parsedExecution,
      status_link,
      script_link,
      filelength,
      edited,
      executed,
      last_run_status,
      retry_count,
      total_run_time_seconds,
      last_run_duration_seconds,
      total_runs,
    });
  }

  // Build new hierarchical structure
  const report = {
    organization,
    repository,
    actions,
  };

  const outPath = path.resolve(process.cwd(), "actions-report.json");
  await fs.writeFile(outPath, JSON.stringify(report, null, 2) + "\n", "utf8");
  console.log(`Wrote ${actions.length} entries to ${outPath}`);

  // Print cache statistics
  console.log(`\n📊 Cache Statistics:`);
  console.log(`   ✓ Cache hits: ${cacheHits}`);
  console.log(`   ✗ Cache misses: ${cacheMisses}`);
  console.log(`   Hit rate: ${actions.length > 0 ? Math.round((cacheHits / actions.length) * 100) : 0}%`);
  console.log(`   Cache directory: ${path.resolve(process.cwd(), CACHE_DIR)}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
