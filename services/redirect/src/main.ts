import type { FastifyInstance } from "fastify";
import type { Redis } from "ioredis";
import type { MongoClient } from "mongodb";
import { reportCacheConnectivity } from "./adapters/cacheConnectivity.js";
import { createMongoClient, createValkeyClient } from "./adapters/clients.js";
import { readSettings } from "./adapters/environment.js";
import { LINKS_COLLECTION, type LinkRecord, MongoLinkSource } from "./adapters/mongoLinkSource.js";
import { MongoReadinessProbe } from "./adapters/mongoReadinessProbe.js";
import { ReadThroughLinkSource } from "./adapters/readThroughLinkSource.js";
import { ValkeyLinkCache } from "./adapters/valkeyLinkCache.js";
import { LinkResolver } from "./domain/linkResolver.js";
import { buildServer } from "./http/server.js";

const CACHE_DEADLINE_MILLISECONDS = 50;

async function start(): Promise<void> {
  const settings = readSettings(process.env);
  const mongoClient = createMongoClient(settings.mongo);
  await mongoClient.connect();
  const database = mongoClient.db(settings.mongo.database);
  const valkeyClient = createValkeyClient(settings.valkey, CACHE_DEADLINE_MILLISECONDS);
  const linkSource = new ReadThroughLinkSource(
    new ValkeyLinkCache(valkeyClient, CACHE_DEADLINE_MILLISECONDS),
    new MongoLinkSource(database.collection<LinkRecord>(LINKS_COLLECTION)),
  );
  const server = buildServer({
    resolver: new LinkResolver(linkSource),
    readiness: new MongoReadinessProbe(database),
    logLevel: settings.logLevel,
  });
  reportCacheConnectivity(valkeyClient, server.log);
  stopOnSignals(() => stopEverything(server, mongoClient, valkeyClient));
  await server.listen({ host: "0.0.0.0", port: settings.port });
}

async function stopEverything(
  server: FastifyInstance,
  mongoClient: MongoClient,
  valkeyClient: Redis,
): Promise<void> {
  await server.close();
  await mongoClient.close();
  valkeyClient.disconnect();
}

function stopOnSignals(stop: () => Promise<void>): void {
  const exitAfterStopping = (): void => {
    stop().then(
      () => process.exit(0),
      () => process.exit(1),
    );
  };
  process.once("SIGTERM", exitAfterStopping);
  process.once("SIGINT", exitAfterStopping);
}

function exitAfterStartupFailure(error: unknown): void {
  const reason = error instanceof Error ? error.message : String(error);
  console.error(`nanolink-redirect could not start: ${reason}`);
  process.exit(1);
}

start().catch(exitAfterStartupFailure);
