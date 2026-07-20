# Current Events Generation Guide (TNPSC Unit II)

This guide codifies the rules, question patterns, and distractor constraints for generating Current Affairs/Current Events practice batches for the TNPSC Group 1 & 2 exams.

---

## 1. Core Generation Rules

### Rule 1: Difficulty Split & Quality Pruning
* **Total Final Questions**: Exactly **30 questions**.
* **Difficulty Split**: Exactly **15 Medium** and **15 Hard** questions.
* **Over-provisioning & Pruning**: Generate **34 questions** (17 Medium, 17 Hard) from the API. Calculate a quality score `len(question_en) + len(explanation)` in Python and discard the 2 shortest/weakest questions in each category.

### Rule 2: Complete Exclusion (Zero Duplicates)
* Before calling the API, the agent **must** load `current_affairs_questions_db.json`, filter by the current `topic`, and pass the English text of all existing questions as a strict exclusion list in the prompt to ensure 100% unique questions.

### Rule 3: Advanced Formats (Rule 5 Partnerships)
Every 30-question practice batch must contain:
1. **Paragraph-Based Inference Questions (Min 4)**: 2–3 sentence data-rich premise. Options test logical deduction rather than rote memory (utilizing qualifiers like *only*, *more than*, *less than*).
2. **Contextual Connect Questions (Min 3)**: Core historical concepts hooked to modern contexts (recent global summits like G20/Y20/COP, recent government schemes, or NITI Aayog meetings).

---

## 2. Core Question Patterns (Syllabus-Learned)

Every current affairs practice batch must contain a balanced mix of these four standard TNPSC question formats:

### Pattern A: Statement-Evaluation (Target: 30% - 40% of Batch)
Evaluates multiple dimensions of a single scheme, summit, or report. 
* **Structure**: Present 2 to 4 numbered statements (1, 2, 3, 4) detailing years, target metrics, or launching bodies.
* **Distractors**: Mix combinations (e.g., "1 and 2 only", "2 and 3 only", "1, 2 and 4", "All the above").

### Pattern B: Match the Following (Target: 15% - 20% of Batch)
Matches lists of related entities (e.g., Schemes $\rightarrow$ Launch Years, Awards $\rightarrow$ Fields, Summits $\rightarrow$ Host Cities).
* **Layout**: Must use our standard 2-column HTML layout:
  ```html
  Match the following:<br><div class='match-container'><div class='match-col-left'>a) Scheme A<br>b) Scheme B<br>c) Scheme C<br>d) Scheme D</div><div class='match-col-right'>1. Year 1<br>2. Year 2<br>3. Year 3<br>4. Year 4</div></div>
  ```
* **Options**: Format option text simply as aligned numbers (e.g., "3   4   1   2").

### Pattern C: Assertion & Reason (Target: 15% - 20% of Batch)
* **Structure**: Provide an Assertion (A) and a Reason (R).
* **Options**:
  * A) Both (A) and (R) are true and (R) is the correct explanation of (A)
  * B) Both (A) and (R) are true but (R) is NOT the correct explanation of (A)
  * C) (A) is true but (R) is false
  * D) (A) is false but (R) is true
  * E) Answer not known / விடை தெரியவில்லை

### Pattern D: Direct MCQ Fact-Checks (Target: 20% - 30% of Batch)
Tests singular, crucial facts (e.g., India's exact rank in a report, a newly appointed head, or a satellite launch vehicle).

---

## 3. Plausible Distractors & Formatting
* **Plausible Distractors**: All incorrect options must use adjacent years, related ministries, standard cost splits (e.g. 60:40 vs 90:10), or close ranking indexes to test candidate precision.
* **Option E**: Every question must include `"key": "E", "text_en": "Answer not known", "text_ta": "விடை தெரியவில்லை"`.
* **Bilingual**: Every question, option, and explanation must be fully translated into Tamil.
