import { FastifyInstance } from "fastify";
import swagger from "@fastify/swagger";


export function registerSwagger(app: FastifyInstance) {
    app.register(swagger, {
        openapi: {
            openapi: '3.0.0',
            info: {
                title: 'Test API',
                description: 'Testing the Fastify swagger API',
                version: '0.1.0'
            },
           
            externalDocs: {
                url: 'https://swagger.io',
                description: 'Find more info here'
            }
        }
    });
}
