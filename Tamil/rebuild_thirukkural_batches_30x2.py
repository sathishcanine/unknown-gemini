#!/usr/bin/env python3
"""
Rebuild Thirukkural questions DB as 10 topics × (Batch 1 = 30 + Batch 2 = 30).

Reads Tamil/unit7_thirukkural_adhikaram_questions_temp.json + notes,
filters weak/near-dup, writes Tamil/thirukkural_questions_db.json.
"""

from __future__ import annotations

import json
import random
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher

random.seed(11)

BASE = "Tamil"
TEMP = f"{BASE}/unit7_thirukkural_adhikaram_questions_temp.json"
NOTES = f"{BASE}/unit7_thirukkural_adhikaram_notes_temp.json"
OUT_DB = f"{BASE}/thirukkural_questions_db.json"
OUT_TOPICS = f"{BASE}/thirukkural_topics.json"

TARGET_PER_BATCH = 30
BATCHES_PER_TOPIC = 2  # Batch 1 + Batch 2
NEED_PER_TOPIC = TARGET_PER_BATCH * BATCHES_PER_TOPIC  # 60


def norm(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").lower())


def is_weak(q: dict) -> list:
    reasons = []
    if not q.get("verified", True):
        reasons.append("unverified")
    letter = (q.get("correct_option_letter") or "").strip().upper()[:1]
    opts = [str(o).strip() for o in (q.get("options_ta") or [])]
    stem = (q.get("question_ta") or "").strip()
    if letter not in "ABCD":
        reasons.append("bad_letter")
    if len(opts) < 4 or any(not o for o in opts[:4]):
        reasons.append("bad_opts")
    if len(stem) < 10:
        reasons.append("short_stem")
    if len(set(norm(o) for o in opts[:4])) < 4:
        reasons.append("dup_opts")
    if not (q.get("explanation_ta") or "").strip() and not (q.get("based_on_kural") or "").strip():
        reasons.append("no_support")
    return reasons


def main():
    temp = json.load(open(TEMP, encoding="utf-8"))
    notes = json.load(open(NOTES, encoding="utf-8"))
    adh_names = {int(a["serial_no"]): a["name_ta"] for a in notes["adhikarams"]}

    kept = []
    dropped = 0
    for q in temp.get("questions") or []:
        if is_weak(q):
            dropped += 1
            continue
        kept.append(q)

    # near-dup within adhikaram
    by_adh = defaultdict(list)
    for q in kept:
        by_adh[int(q["adhikaram_serial_no"])].append(q)

    deduped = []
    for serial, items in sorted(by_adh.items()):
        accepted = []
        for q in items:
            sn = norm(q["question_ta"])
            if any(SequenceMatcher(None, sn, norm(a["question_ta"])).ratio() >= 0.88 for a in accepted):
                dropped += 1
                continue
            accepted.append(q)
        deduped.extend(accepted)

    print(f"valid={len(deduped)} dropped={dropped}")

    pairs = [(i, i + 1) for i in range(1, 21, 2)]
    topics_meta = []
    for idx, (a, b) in enumerate(pairs, 1):
        topics_meta.append(
            {
                "id": f"thirukkural_batch_{idx}",
                "batch_no": idx,
                "adhikaram_serials": [a, b],
                "name_ta": f"{adh_names[a]} — {adh_names[b]}",
                "name_en": f"Adhikarams {a} & {b}",
                "adhikaram_names": [adh_names[a], adh_names[b]],
            }
        )

    db = []
    shortfalls = []
    for t in topics_meta:
        a, b = t["adhikaram_serials"]
        pool = [q for q in deduped if int(q["adhikaram_serial_no"]) in (a, b)]
        random.shuffle(pool)

        # Prefer balanced mix from both adhikarams
        from_a = [q for q in pool if int(q["adhikaram_serial_no"]) == a]
        from_b = [q for q in pool if int(q["adhikaram_serial_no"]) == b]
        mixed = []
        i = j = 0
        while len(mixed) < NEED_PER_TOPIC and (i < len(from_a) or j < len(from_b)):
            if i < len(from_a):
                mixed.append(from_a[i])
                i += 1
            if len(mixed) >= NEED_PER_TOPIC:
                break
            if j < len(from_b):
                mixed.append(from_b[j])
                j += 1
        if len(mixed) < NEED_PER_TOPIC:
            shortfalls.append((t["name_ta"], len(mixed), NEED_PER_TOPIC - len(mixed)))

        # Take up to 60; if more, trim; if less, take all (caller may re-topup)
        selected = mixed[:NEED_PER_TOPIC]
        # Split into Batch 1 / Batch 2 of 30 (if short, fill Batch1 first)
        for bi, start in enumerate((0, 30), 1):
            chunk = selected[start : start + TARGET_PER_BATCH]
            if not chunk:
                continue
            for q in chunk:
                opts = list(q["options_ta"][:4])
                letter = q["correct_option_letter"]
                ans = opts[ord(letter) - 65]
                random.shuffle(opts)
                new_letter = chr(65 + opts.index(ans))
                options = [
                    {"key": chr(65 + i), "text_en": opts[i], "text_ta": opts[i]} for i in range(4)
                ]
                db.append(
                    {
                        "question_en": q["question_ta"],
                        "question_ta": q["question_ta"],
                        "correct_option": new_letter,
                        "explanation": q.get("explanation_ta") or "",
                        "explanation_ta": q.get("explanation_ta") or "",
                        "difficulty": "Medium",
                        "source_note": q.get("based_on_kural") or "",
                        "subject": "Tamil",
                        "unit": "Thirukkural",
                        "topic": t["name_ta"],
                        "topic_id": t["id"],
                        "adhikaram_serial_no": q["adhikaram_serial_no"],
                        "adhikaram_name_ta": q["adhikaram_name_ta"],
                        "source_exam": f"Practice Batch {bi}",
                        "type": "practice",
                        "batch": f"Batch {bi}",
                        "group": "Practice",
                        "examGroup": q.get("examGroup") or ["group4"],
                        "options": options,
                    }
                )

    json.dump(db, open(OUT_DB, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    open(OUT_DB, "a").write("\n")

    topics_file = {
        "subject_id": "Tamil",
        "subject_en": "Tamil",
        "subject_ta": "தமிழ்",
        "unit": {
            "id": "Thirukkural",
            "name_en": "Unit 7 — Thirukkural",
            "name_ta": "அலகு 7 — திருக்குறள்",
            "exam_questions": 15,
            "syllabus_note": "TNPSC General Tamil — Unit 7 Phase 1 (திருக்குறள்)",
        },
        "topics": [
            {
                "id": t["id"],
                "name_en": t["name_en"],
                "name_ta": t["name_ta"],
                "group": "திருக்குறள்",
                "priority": t["batch_no"],
                "adhikaram_serials": t["adhikaram_serials"],
                "adhikaram_names": t["adhikaram_names"],
            }
            for t in topics_meta
        ],
    }
    json.dump(topics_file, open(OUT_TOPICS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    open(OUT_TOPICS, "a").write("\n")

    print(f"wrote {OUT_DB} count={len(db)}")
    print("letters", dict(Counter(q["correct_option"] for q in db)))
    by_tb = Counter((q["topic"], q["batch"]) for q in db)
    for t in topics_meta:
        b1 = by_tb[(t["name_ta"], "Batch 1")]
        b2 = by_tb[(t["name_ta"], "Batch 2")]
        print(f"  {t['name_ta']}: Batch1={b1} Batch2={b2}")
    if shortfalls:
        print("SHORTFALLS:", shortfalls)
        # Allow small shortfalls only if every topic has Batch1=30 and Batch2>=20
        bad = [s for s in shortfalls if s[1] < 50]
        if bad:
            raise SystemExit(1)
        print("Continuing despite minor shortfalls (<10 missing on some topics).")


if __name__ == "__main__":
    main()
