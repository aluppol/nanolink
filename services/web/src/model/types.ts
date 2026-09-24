export type ViewName = "mine" | "all";

export interface Link {
  readonly id: string;
  readonly shortCode: string;
  readonly shortUrl: string;
  readonly longUrl: string;
  readonly ownerId: string;
  readonly createdAt: string;
  readonly updatedAt: string;
}

export interface LinkPage {
  readonly links: readonly Link[];
  readonly nextCursor: string | null;
}

export interface Me {
  readonly userId: string;
  readonly username: string;
  readonly roles: readonly string[];
  readonly isGuest: boolean;
  readonly isAdmin: boolean;
  readonly dailyQuota: number | null;
  readonly createdToday: number;
}

export type TaskStatus = "queued" | "created" | "failed";

export interface TaskResult {
  readonly taskId: string;
  readonly status: TaskStatus;
  readonly link: Link | null;
  readonly failure: string | null;
}

export interface QueuedTask {
  readonly taskId: string;
}
