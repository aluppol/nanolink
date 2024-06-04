export interface UrlsRepository {
    read(shortUrl: string): UrlRecord
}

export interface UrlRecord {
    id: string,
    longUrl: string,
}