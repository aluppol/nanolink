import type { Link, LinkPage, Me, QueuedTask, TaskResult, TaskStatus } from "./types";

type JsonObject = Readonly<Record<string, unknown>>;

const linkFields = ["id", "short_code", "short_url", "long_url", "owner_id", "created_at"] as const;
const taskStatuses: readonly TaskStatus[] = ["queued", "created", "failed"];

export function parseLink(value: unknown): Link | null {
  const source = asObject(value);
  const fields = source === null ? null : requiredTexts(source, linkFields);
  if (source === null || fields === null) {
    return null;
  }
  return {
    id: fields.id,
    shortCode: fields.short_code,
    shortUrl: fields.short_url,
    longUrl: fields.long_url,
    ownerId: fields.owner_id,
    createdAt: fields.created_at,
    updatedAt: textField(source, "updated_at") ?? fields.created_at,
  };
}

export function parseLinkPage(value: unknown): LinkPage | null {
  const source = asObject(value);
  const items = source?.links;
  if (source === null || !Array.isArray(items)) {
    return null;
  }
  const links = items.map(parseLink).filter((link): link is Link => link !== null);
  if (links.length !== items.length) {
    return null;
  }
  return { links, nextCursor: textField(source, "next_cursor") };
}

export function parseMe(value: unknown): Me | null {
  const source = asObject(value);
  const userId = source === null ? null : textField(source, "user_id");
  if (source === null || userId === null) {
    return null;
  }
  const roles = parseRoles(source.roles);
  return {
    userId,
    username: textField(source, "username") ?? userId,
    roles,
    isGuest: flagField(source, "is_guest") ?? roles.includes("guest"),
    isAdmin: flagField(source, "is_admin") ?? roles.includes("ADMIN"),
    dailyQuota: countField(source, "daily_quota"),
    createdToday: countField(source, "created_today") ?? 0,
  };
}

export function parseTaskResult(value: unknown): TaskResult | null {
  const source = asObject(value);
  const taskId = source === null ? null : textField(source, "task_id");
  const status = parseTaskStatus(source?.status);
  if (source === null || taskId === null || status === null) {
    return null;
  }
  const link = source.link === null || source.link === undefined ? null : parseLink(source.link);
  if (status === "created" && link === null) {
    return null;
  }
  return { taskId, status, link, failure: textField(source, "failure") };
}

export function parseQueuedTask(value: unknown): QueuedTask | null {
  const source = asObject(value);
  const taskId = source === null ? null : textField(source, "task_id");
  return taskId === null ? null : { taskId };
}

function asObject(value: unknown): JsonObject | null {
  const isPlainObject = typeof value === "object" && value !== null && !Array.isArray(value);
  return isPlainObject ? (value as JsonObject) : null;
}

function requiredTexts<Name extends string>(
  source: JsonObject,
  names: readonly Name[],
): Record<Name, string> | null {
  const found: Partial<Record<Name, string>> = {};
  for (const name of names) {
    const value = source[name];
    if (typeof value !== "string") {
      return null;
    }
    found[name] = value;
  }
  return found as Record<Name, string>;
}

function textField(source: JsonObject, name: string): string | null {
  const value = source[name];
  return typeof value === "string" ? value : null;
}

function flagField(source: JsonObject, name: string): boolean | null {
  const value = source[name];
  return typeof value === "boolean" ? value : null;
}

function countField(source: JsonObject, name: string): number | null {
  const value = source[name];
  return typeof value === "number" && Number.isInteger(value) && value >= 0 ? value : null;
}

function parseRoles(value: unknown): readonly string[] {
  return Array.isArray(value)
    ? value.filter((role): role is string => typeof role === "string")
    : [];
}

function parseTaskStatus(value: unknown): TaskStatus | null {
  return taskStatuses.find((status) => status === value) ?? null;
}
