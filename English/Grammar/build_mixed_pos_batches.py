#!/usr/bin/env python3
"""Build Mixed Part of Speech: 4 batches × 25 Q from existing POS practice set.

Each Mixed batch intentionally spans all 8 POS topics (≈3 each + 1 filler).
"""

from __future__ import annotations

import copy
import json
import os
import random
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(ROOT, "English", "Grammar", "parts_of_speech_questions_db.json")

MIXED_TOPIC = "Mixed Part of Speech Questions"
MIXED_TOPIC_ID = "mixed_part_of_speech_questions"
MIXED_TOPIC_TA = "கலப்பு பேச்சின் பகுதிகள்"
POS_ORDER = [
    "Noun",
    "Pronoun",
    "Adjective",
    "Verb",
    "Adverb",
    "Preposition",
    "Conjunction",
    "Interjection",
]
BATCH_COUNT = 4
PER_BATCH = 25
SEED = 42


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

    pointers = {t: 0 for t in POS_ORDER}

    def take(topic: str, n: int) -> list:
        out = []
        while len(out) < n:
            i = pointers[topic]
            if i >= len(by_topic[topic]):
                break
            out.append(by_topic[topic][i])
            pointers[topic] = i + 1
        return out

    batches: list[list] = []
    for bi in range(BATCH_COUNT):
        batch_qs: list = []
        # 3 from each of 8 topics = 24
        for topic in POS_ORDER:
            batch_qs.extend(take(topic, 3))
        # +1 filler rotating through topics
        filler_topic = POS_ORDER[bi % len(POS_ORDER)]
        extra = take(filler_topic, 1)
        if not extra:
            # fallback: any remaining topic
            for topic in POS_ORDER:
                extra = take(topic, 1)
                if extra:
                    break
        batch_qs.extend(extra)
        if len(batch_qs) != PER_BATCH:
            raise SystemExit(
                f"Batch {bi + 1} has {len(batch_qs)} Q (want {PER_BATCH}); "
                f"pointers={pointers}"
            )
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
            row["batch"] = f"Batch {bi}"
            row["source_exam"] = f"Practice Mixed Batch {bi}"
            row["group"] = "mixed_pos"
            row["source_note"] = f"Reused from {src_topic} / {src_batch}"
            new_rows.append(row)

    out = kept + new_rows
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Wrote {len(out)} total questions ({len(new_rows)} Mixed)")
    for bi in range(1, BATCH_COUNT + 1):
        batch = [q for q in new_rows if q["batch"] == f"Batch {bi}"]
        srcs = Counter()
        for q in batch:
            note = q.get("source_note") or ""
            if note.startswith("Reused from "):
                srcs[note[len("Reused from ") :].split(" / ")[0]] += 1
        print(f"  Batch {bi}: {len(batch)} Q — mix {dict(srcs)}")


if __name__ == "__main__":
    main()
