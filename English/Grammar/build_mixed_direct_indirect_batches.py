#!/usr/bin/env python3
"""Build Mixed Direct & Indirect Speech: 5 batches × 25 Q from existing 5-topic set."""

from __future__ import annotations

import copy
import json
import os
import random
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(ROOT, "English", "Grammar", "direct_indirect_questions_db.json")

MIXED_TOPIC = "Mixed Direct & Indirect Speech"
MIXED_TOPIC_ID = "mixed_direct_indirect"
MIXED_TOPIC_TA = "கலப்பு நேரடி & மறைமுக பேச்சு"
TOPIC_ORDER = [
    "Statements (Direct → Indirect)",
    "Questions (WH & Yes/No)",
    "Commands, Requests & Imperatives",
    "Indirect → Direct",
    "Time, Place, Pronoun & Reporting Verbs",
]
BATCH_COUNT = 5
PER_BATCH = 25
BASE_PER_TOPIC = 5
SEED = 43


def main() -> None:
    with open(DB_PATH, "r", encoding="utf-8") as f:
        questions = json.load(f)

    pool = [
        q
        for q in questions
        if (q.get("topic") or "").strip() != MIXED_TOPIC
        and (q.get("type") or "practice") == "practice"
    ]

    by_topic: dict[str, list] = defaultdict(list)
    for q in pool:
        by_topic[(q.get("topic") or "Other").strip()].append(q)

    rng = random.Random(SEED)
    for topic in by_topic:
        rng.shuffle(by_topic[topic])

    pointers = {t: 0 for t in TOPIC_ORDER}

    def take(topic: str, n: int) -> list:
        out = []
        while len(out) < n:
            i = pointers.get(topic, 0)
            if i >= len(by_topic.get(topic) or []):
                break
            out.append(by_topic[topic][i])
            pointers[topic] = i + 1
        return out

    batches: list[list] = []
    for bi in range(BATCH_COUNT):
        batch_qs: list = []
        for topic in TOPIC_ORDER:
            got = take(topic, BASE_PER_TOPIC)
            if len(got) < BASE_PER_TOPIC:
                raise SystemExit(
                    f"Need {BASE_PER_TOPIC} from {topic} for mixed batch {bi+1}, got {len(got)}"
                )
            batch_qs.extend(got)
        if len(batch_qs) != PER_BATCH:
            raise SystemExit(f"Batch {bi+1} has {len(batch_qs)}")
        rng.shuffle(batch_qs)
        batches.append(batch_qs)

    kept = [q for q in questions if (q.get("topic") or "").strip() != MIXED_TOPIC]
    new_rows = []
    for bi, batch_qs in enumerate(batches, start=1):
        for q in batch_qs:
            row = copy.deepcopy(q)
            src_topic = (q.get("topic") or "").strip()
            src_batch = (q.get("batch") or "").strip()
            row["topic"] = MIXED_TOPIC
            row["topic_id"] = MIXED_TOPIC_ID
            row["topic_ta"] = MIXED_TOPIC_TA
            row["menu"] = "Direct & Indirect Speech"
            row["batch"] = f"Batch {bi}"
            row["source_exam"] = f"Practice Mixed Batch {bi}"
            row["group"] = "mixed_direct_indirect"
            row["source_note"] = f"Reused from {src_topic} / {src_batch}"
            new_rows.append(row)

    out = kept + new_rows
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Wrote {len(out)} total ({len(new_rows)} Mixed)")
    for bi in range(1, BATCH_COUNT + 1):
        batch = [q for q in new_rows if q["batch"] == f"Batch {bi}"]
        srcs = Counter()
        for q in batch:
            note = q.get("source_note") or ""
            if note.startswith("Reused from "):
                srcs[note[len("Reused from ") :].split(" / ")[0]] += 1
        print(f"  Batch {bi}: {len(batch)} Q — {dict(srcs)}")


if __name__ == "__main__":
    main()
