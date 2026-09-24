import { Redis } from "ioredis";
import { MongoClient } from "mongodb";
import type { MongoSettings, ValkeySettings } from "./environment.js";

const MAXIMUM_RECONNECT_DELAY_MILLISECONDS = 2000;

export function createMongoClient(settings: MongoSettings): MongoClient {
  return new MongoClient(`mongodb://${settings.host}:${settings.port}/${settings.database}`, {
    auth: { username: settings.username, password: settings.password },
    authSource: settings.database,
    appName: "nanolink-redirect",
    maxPoolSize: 50,
    serverSelectionTimeoutMS: 2000,
    connectTimeoutMS: 2000,
    socketTimeoutMS: 5000,
  });
}

export function createValkeyClient(
  settings: ValkeySettings,
  commandTimeoutMilliseconds: number,
): Redis {
  return new Redis({
    host: settings.host,
    port: settings.port,
    password: settings.password,
    enableOfflineQueue: false,
    maxRetriesPerRequest: 0,
    commandTimeout: commandTimeoutMilliseconds,
    connectTimeout: 1000,
    enableAutoPipelining: true,
    retryStrategy: reconnectDelayMilliseconds,
  });
}

function reconnectDelayMilliseconds(attempt: number): number {
  return Math.min(attempt * 200, MAXIMUM_RECONNECT_DELAY_MILLISECONDS);
}
