import { ObjectId } from "mongodb";

export interface IUrlData {
    _id: ObjectId,
    long_url: string, 
}

export class Url {
    public id: ObjectId;
    public long_url: string;

    constructor({ _id, long_url }: IUrlData) {
        this.id = _id;
        this.long_url = long_url;
    }
}