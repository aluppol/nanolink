import fastify from "fastify"
import { JsonSchemaToTsProvider } from "@fastify/type-provider-json-schema-to-ts";
import { fastifyAwilixPlugin } from "@fastify/awilix";

import { redirectController } from "./redirectController"
import { get_env_variable } from "./utils/get_env_variable";
import { setupDI, registerSwagger, registerDatabase } from "./config";



async function start_server() {
    
    const server = fastify({
        logger: true,
    }).withTypeProvider<JsonSchemaToTsProvider>();

    try {
        server.get("/ping", async (req, res) => {
            return {
                status: "ok",
                timestamp: new Date().toISOString(),
                message: "Welcom to Redirect API Service. See /docs for documentation"
            }
        });
        
        registerSwagger(server);

        registerDatabase(server, {
            uri: `mongodb://${get_env_variable("DB_REDIRECT_USER")}:${get_env_variable("DB_REDIRECT_PASS")}@${get_env_variable("DB_HOST")}:${get_env_variable("DB_PORT")}/${get_env_variable("DB_NAME")}`,
            options: { forceClose: true, minPoolSize: 1 }
        });
    
        server.register(fastifyAwilixPlugin, { disposeOnClose: true,  disposeOnResponse: true, strictBooleanEnforced: true, container: setupDI(server) });
        
        server.register(redirectController);
        
        const PORT = Number(get_env_variable("REDIRECT_API_PORT"));
        
        server.listen({port: PORT || 8080, host: '0.0.0.0'}, (err, address) => {
            if (err) {
    
            }
            else {
                server.log.info(`Server is listening on ${address}`);
            }
        });
    } catch(err) {
        server.log.error(err);
        process.exit(1);
    }

    
}

start_server();