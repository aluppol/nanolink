import fastify from "fastify"
import { JsonSchemaToTsProvider } from "@fastify/type-provider-json-schema-to-ts";
import { redirectController } from "./redirectController"

const server = fastify({
    logger: true,
}).withTypeProvider<JsonSchemaToTsProvider>();;


server.get('/ping', async (req, res) => {
    return {
        status: "ok",
        timestamp: new Date().toISOString(),
        message: "Welcom to Redirect API Service. See /docs for documentation"
    }
});

server.register(redirectController)

const PORT = Number(process.env.REDIRECT_API_PORT)
if (!PORT){
    throw new Error("Env var 'PORT' is not set.")
}

server.listen({port: PORT || 8080}, (err, address) => {
    if (err) {
        console.error(err);
        process.exit(1);
    }
    else {
        console.log(`Server is listening on ${address}`);
    }
});