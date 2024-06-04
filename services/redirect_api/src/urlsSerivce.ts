import { UrlsRepository } from "./urlsRepository"

class UrlsService {
    private __urlsRepository: UrlsRepository;

    constructor(urlsRepo: UrlsRepository) {
        this.__urlsRepository = urlsRepo
    }
}