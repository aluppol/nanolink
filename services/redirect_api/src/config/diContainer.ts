import { AwilixContainer, Lifetime, asClass, asFunction, createContainer } from "awilix";
import { FastifyInstance } from "fastify/types/instance";

import { IUrlRepository, UrlRepository } from "../repositories";
import { IUrlService, UrlService } from "../services";
import type { Db } from "mongodb";

interface ICradle {
    db: Db;
    urlRepository: IUrlRepository;
    urlService: IUrlService;
}


export function setupDI(app: FastifyInstance): AwilixContainer {
    const container = createContainer<ICradle>({
        strict: true,
    });
    
    container.register({
        db: asFunction(() => app.mongo.db as Db, { lifetime: Lifetime.SINGLETON }),

        urlRepository: asClass(UrlRepository, { lifetime: Lifetime.SINGLETON }).inject((cont) => ({db: cont.resolve("db")})),

        urlService: asClass(UrlService, { lifetime: Lifetime.SINGLETON }).inject((cont) => ({ urlRepository: cont.resolve("urlRepository") }))

    });
    return container;
}