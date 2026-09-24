from bson import ObjectId

from nanolink.adapters.mongo.documents import (
    document_from_draft,
    link_from_document,
    object_id_or_none,
    report_fields,
    task_record_from_document,
)
from nanolink.adapters.nats.inbox import retry_delay
from nanolink.adapters.nats.messages import decode_result, decode_task, encode_result, encode_task
from nanolink.adapters.short_codes import SecretsShortCodeGenerator
from nanolink.domain.links import Link, LinkDraft
from nanolink.domain.short_codes import is_reserved_short_code, is_short_code
from nanolink.domain.tasks import CreateLinkTask, TaskRecord, TaskReport, TaskResult, TaskStatus
from tests.support import FIXED_TIME, report_mismatches

LINK = Link(
    "65f0c1f6e8a3b4c2d9e1f0a1", "aB3xY9", "https://example.com/", "alice-0001", FIXED_TIME, FIXED_TIME
)
TASK = CreateLinkTask("task-1", "alice-0001", "https://example.com/", "alice@example.org")
RESULTS = [
    TaskResult(TaskReport("task-1", "alice-0001", TaskStatus.CREATED, LINK, None), "alice@example.org"),
    TaskResult(TaskReport("task-2", "sandbox", TaskStatus.FAILED, None, "no free short code"), None),
]


def test_queue_messages_round_trip() -> None:
    mismatches = [] if decode_task(encode_task(TASK)) == TASK else ["task did not survive the round trip"]
    mismatches += [
        f"result {result.report.task_id} did not survive the round trip"
        for result in RESULTS
        if decode_result(encode_result(result)) != result
    ]
    report_mismatches(mismatches)


MALFORMED = [b"", b"not json", b"{}", b'{"task_id": 1}', b'{"task_id":"t","owner_id":"o"}']


def test_malformed_queue_messages_are_rejected() -> None:
    accepted = [payload for payload in MALFORMED if decode_task(payload) is not None]
    accepted += [payload for payload in MALFORMED if decode_result(payload) is not None]
    assert accepted == []


def test_link_documents_map_both_ways() -> None:
    draft = LinkDraft("task-1", "aB3xY9", "https://example.com/", "alice-0001")
    document = {"_id": ObjectId(LINK.id), **document_from_draft(draft, FIXED_TIME)}
    assert document["deleted_at"] is None
    assert document["task_id"] == "task-1"
    assert link_from_document(document) == LINK


def test_task_documents_map_both_ways() -> None:
    report = TaskReport("task-1", "alice-0001", TaskStatus.CREATED, LINK, None)
    document = {"_id": "task-1", "owner_id": "alice-0001", **report_fields(report, FIXED_TIME)}
    expected = TaskRecord("task-1", "alice-0001", TaskStatus.CREATED, LINK.id, None)
    assert task_record_from_document(document) == expected


OBJECT_ID_CASES = [
    ("24 hex characters", "65f0c1f6e8a3b4c2d9e1f0a1", True),
    ("upper-case hex", "65F0C1F6E8A3B4C2D9E1F0A1", False),
    ("12 characters", "aaaaaaaaaaaa", False),
    ("not hex", "zzzzzzzzzzzzzzzzzzzzzzzz", False),
]


def test_object_ids_are_parsed_strictly() -> None:
    mismatches = [
        case_id
        for case_id, candidate, valid in OBJECT_ID_CASES
        if (object_id_or_none(candidate) is not None) != valid
    ]
    report_mismatches(mismatches)


def test_retry_delays_grow_and_stay_bounded() -> None:
    delays = [retry_delay(deliveries) for deliveries in range(9)]
    assert delays == [2.0, 2.0, 10.0, 30.0, 60.0, 120.0, 120.0, 120.0, 120.0]


def test_generated_codes_are_valid_and_never_reserved() -> None:
    generator = SecretsShortCodeGenerator()
    codes = [generator.next_code() for _ in range(2000)]
    assert all(is_short_code(code) and not is_reserved_short_code(code) for code in codes)
    assert len(set(codes)) > 1990
