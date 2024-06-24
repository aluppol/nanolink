import { Collection, Db } from 'mongodb';
import { IUrlData, Url } from '../models';
import { get_env_variable } from '../utils';


interface ICradle {
    db: Db;
}

export interface IUrlRepository {
    read(shortUrl: string): Promise<Url | null>
}

export class UrlRepository implements IUrlRepository {
    private __collection: Collection;
    constructor ({ db }: ICradle){
        this.__collection = db.collection(get_env_variable("DB_URLS_COLLECTION_NAME"));
    }

    async read(shortUrl: string): Promise<Url | null> {
        const url_data = await this.__collection.findOne<IUrlData>({ short_url: shortUrl }, { projection: { _id: 1, long_url: 1 }});
        return url_data ? new Url(url_data) : null;
    }
}