import fastifyMongodb from "@fastify/mongodb";
import type { FastifyMongodbOptions } from "@fastify/mongodb";
import { FastifyInstance } from "fastify";


interface DBPluginOptions {
    uri: string;
    options?: FastifyMongodbOptions;
}

export async function registerDatabase(
    app: FastifyInstance,
    { uri,  options }: DBPluginOptions,
): Promise<void> {
    try {
        await app.register(fastifyMongodb, { url: uri, ...options});

        if (!app.mongo.db) {
            throw new Error("No DB in app registered.");
        }

        await app.mongo.db.command({ ping: 1 });
        app.log.info('fastify-mongodb plugin registered and ping check successful');

        app.log.info("Mongodb connected");
    } catch (e) {
        app.log.error("Failed to connect to Mongodb");
        throw e;
    }
}
