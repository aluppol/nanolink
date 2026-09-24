import type { Db } from "mongodb";
import type { ReadinessProbe } from "../domain/readinessProbe.js";

const PING_TIMEOUT_MILLISECONDS = 1000;

export class MongoReadinessProbe implements ReadinessProbe {
  readonly #database: Db;

  constructor(database: Db) {
    this.#database = database;
  }

  async isReady(): Promise<boolean> {
    try {
      await this.#database.command({ ping: 1 }, { timeoutMS: PING_TIMEOUT_MILLISECONDS });
      return true;
    } catch {
      return false;
    }
  }
}
