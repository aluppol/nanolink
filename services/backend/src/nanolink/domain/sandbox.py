from dataclasses import dataclass

from nanolink.domain.links import LinkDraft

SANDBOX_OWNER_ID = "sandbox"
SEED_TASK_PREFIX = "seed-"


@dataclass(frozen=True, slots=True)
class SeedLink:
    short_code: str
    long_url: str


DEMO_LINK_SEEDS: tuple[SeedLink, ...] = (
    SeedLink("NanoGH", "https://github.com/aluppol/nanolink"),
    SeedLink("Albert", "https://albert.luppol.com/"),
    SeedLink("MongoD", "https://www.mongodb.com/docs/manual/"),
    SeedLink("NatsJS", "https://docs.nats.io/nats-concepts/jetstream"),
    SeedLink("Valkey", "https://valkey.io/"),
    SeedLink("Fstify", "https://fastify.dev/"),
)

DEMO_SEED_CODES = frozenset(seed.short_code for seed in DEMO_LINK_SEEDS)


def seed_drafts() -> list[LinkDraft]:
    return [
        LinkDraft(f"{SEED_TASK_PREFIX}{seed.short_code}", seed.short_code, seed.long_url, SANDBOX_OWNER_ID)
        for seed in DEMO_LINK_SEEDS
    ]
