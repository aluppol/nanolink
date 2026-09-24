import type { EventEmitter } from "node:events";

export interface ConnectivityLog {
  info(message: string): void;
  warn(details: { readonly reason: string }, message: string): void;
}

type Connectivity = "unknown" | "reachable" | "unreachable";

export function reportCacheConnectivity(client: EventEmitter, log: ConnectivityLog): void {
  let connectivity: Connectivity = "unknown";
  client.on("ready", () => {
    if (connectivity !== "reachable") {
      log.info("cache reachable");
    }
    connectivity = "reachable";
  });
  client.on("error", (error: Error) => {
    if (connectivity !== "unreachable") {
      log.warn({ reason: error.message }, "cache unreachable, reading links from MongoDB");
    }
    connectivity = "unreachable";
  });
}
