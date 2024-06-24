import { FastifyRequest } from "fastify";
import { IUrlRepository } from "../repositories/urlRepository"
import { Db, ObjectId } from "mongodb";


interface ICradle {
    urlRepository: IUrlRepository;
}

export interface IUrlService {
    getLongUrl(shortUrl: string, req: FastifyRequest): Promise<string | null>;
}

export class UrlService implements IUrlService {
    private __urlRepository: IUrlRepository;

    constructor({ urlRepository }: ICradle) {
        this.__urlRepository = urlRepository;
    }

    public async getLongUrl(shortUrl: string, req: FastifyRequest): Promise<string | null> {
        const url = await this.__urlRepository.read(shortUrl);
        if (url) {
            const info = this.__getUserInfo(req);
            await this.__log_stats(url.id, info)
            return url.long_url;
        }
        // log attempt
        return null
    }

    private __getUserInfo(req: FastifyRequest): string {
        return 'info'
    }

    private async __log_stats(urlId: ObjectId, data: string) {
        // TODO
        console.log(`Got url with id: ${urlId}`);
    }
}