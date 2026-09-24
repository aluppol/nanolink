import type { Collection } from "mongodb";
import {
  activeLink,
  DELETED_LINK,
  type LinkResolution,
  MISSING_LINK,
} from "../domain/linkResolution.js";
import type { LinkSource } from "../domain/linkSource.js";

export interface LinkRecord {
  readonly short_code: string;
  readonly long_url: string;
  readonly deleted_at: Date | null;
}

export type ResolvableLinkRecord = Pick<LinkRecord, "long_url" | "deleted_at">;

export const LINKS_COLLECTION = "links";

const RESOLVABLE_FIELDS = { _id: 0, long_url: 1, deleted_at: 1 } as const;

export class MongoLinkSource implements LinkSource {
  readonly #links: Collection<LinkRecord>;

  constructor(links: Collection<LinkRecord>) {
    this.#links = links;
  }

  async resolve(shortCode: string): Promise<LinkResolution> {
    const record = await this.#links.findOne<ResolvableLinkRecord>(
      { short_code: shortCode },
      { projection: RESOLVABLE_FIELDS },
    );
    return resolutionOf(record);
  }
}

export function resolutionOf(record: ResolvableLinkRecord | null): LinkResolution {
  if (record === null) {
    return MISSING_LINK;
  }
  return record.deleted_at == null ? activeLink(record.long_url) : DELETED_LINK;
}
