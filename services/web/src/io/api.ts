import {
  type ApiFailure,
  networkFailure,
  parseApiFailure,
  sessionEnded,
  unreadableResponse,
} from "../model/apiFailure";
import {
  parseLink,
  parseLinkPage,
  parseMe,
  parseQueuedTask,
  parseTaskResult,
} from "../model/parse";
import type { Link, LinkPage, Me, QueuedTask, TaskResult } from "../model/types";

export type Outcome<Value> =
  | { readonly ok: true; readonly value: Value }
  | { readonly ok: false; readonly failure: ApiFailure };

export interface Api {
  fetchMe(): Promise<Outcome<Me>>;
  fetchMyLinks(cursor: string | null): Promise<Outcome<LinkPage>>;
  fetchAllLinks(cursor: string | null): Promise<Outcome<LinkPage>>;
  queueLink(longUrl: string): Promise<Outcome<QueuedTask>>;
  fetchTask(taskId: string): Promise<Outcome<TaskResult>>;
  changeLinkTarget(linkId: string, longUrl: string): Promise<Outcome<Link>>;
  deleteMyLink(linkId: string): Promise<Outcome<true>>;
  deleteAnyLink(linkId: string): Promise<Outcome<true>>;
}

type Parser<Value> = (body: unknown) => Value | null;

const pageSize = 20;
const acknowledged: Parser<true> = () => true;

export const httpApi: Api = {
  fetchMe: () => requestJson("/api/me", { method: "GET" }, parseMe),
  fetchMyLinks: (cursor) =>
    requestJson(pagePath("/api/links", cursor), { method: "GET" }, parseLinkPage),
  fetchAllLinks: (cursor) =>
    requestJson(pagePath("/api/admin/links", cursor), { method: "GET" }, parseLinkPage),
  queueLink: (longUrl) =>
    requestJson("/api/links", jsonRequest("POST", { long_url: longUrl }), parseQueuedTask),
  fetchTask: (taskId) =>
    requestJson(itemPath("/api/tasks", taskId), { method: "GET" }, parseTaskResult),
  changeLinkTarget: (linkId, longUrl) =>
    requestJson(
      itemPath("/api/links", linkId),
      jsonRequest("PATCH", { long_url: longUrl }),
      parseLink,
    ),
  deleteMyLink: (linkId) =>
    requestJson(itemPath("/api/links", linkId), { method: "DELETE" }, acknowledged),
  deleteAnyLink: (linkId) =>
    requestJson(itemPath("/api/admin/links", linkId), { method: "DELETE" }, acknowledged),
};

async function requestJson<Value>(
  path: string,
  init: RequestInit,
  parse: Parser<Value>,
): Promise<Outcome<Value>> {
  const response = await send(path, init);
  if (!(response instanceof Response)) {
    return { ok: false, failure: response };
  }
  if (response.type === "opaqueredirect") {
    return { ok: false, failure: sessionEnded() };
  }
  const body = await readJson(response);
  if (!response.ok) {
    return { ok: false, failure: parseApiFailure(response.status, body) };
  }
  const value = parse(body);
  return value === null
    ? { ok: false, failure: unreadableResponse(response.status) }
    : { ok: true, value };
}

async function send(path: string, init: RequestInit): Promise<Response | ApiFailure> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  try {
    return await fetch(path, {
      ...init,
      headers,
      credentials: "same-origin",
      redirect: "manual",
      cache: "no-store",
    });
  } catch {
    return networkFailure();
  }
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function jsonRequest(method: string, body: Readonly<Record<string, string>>): RequestInit {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

function pagePath(base: string, cursor: string | null): string {
  const query = new URLSearchParams({ limit: String(pageSize) });
  if (cursor !== null) {
    query.set("cursor", cursor);
  }
  return `${base}?${query.toString()}`;
}

function itemPath(base: string, id: string): string {
  return `${base}/${encodeURIComponent(id)}`;
}
