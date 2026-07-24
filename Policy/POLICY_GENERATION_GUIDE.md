# Policy Notes Generation Guide (Tamil Nadu State Policy Notes)

This guide codifies the rules, question patterns, and distractor constraints for generating Policy Notes practice batches for the TNPSC Group 1 & 2 exams.

---

## 1. Core Generation Rules

### Rule 1: Difficulty Split & Quality Pruning
* **Total Final Questions**: Exactly **30 questions**.
* **Difficulty Split**: Roughly **17 Medium** and **13 Hard** questions (does not have to be exactly 17/13; splits like 18/12, 16/14, or 15/15 are fully acceptable).
* **Over-provisioning & Dynamic Selection**:
  * Generate **32 questions** (18 Medium, 14 Hard) from the API.
  * Filter out invalid questions and sort the remaining lists by quality score (`len(question_en) + len(explanation)` descending).
  * Dynamically select the 30 best questions: If there are fewer than 13 Hard questions, take all available Hard questions and make up the remainder from Medium (e.g., 18 Medium / 12 Hard); if there are fewer than 17 Medium, take all available Medium and make up the remainder from Hard; otherwise, select 17 Medium and 13 Hard. This discards the shortest/weakest questions while ensuring a total of 30.

### Rule 2: Complete Pool Analysis & Zero Duplicates
* **No Fact Slicing**: For every batch (including Batch 1, Batch 2, and onward), the generator script **must** load and analyze the **entire pool of facts** for that topic, rather than slicing them into subsets.
* **Strict Question Exclusion**: To guarantee zero duplication, the script loads all existing questions from `policy_questions_db.json` for that topic and passes their English text as a strict exclusion list. The API will choose from the entire fact pool but must craft entirely new questions that do not duplicate the existing ones.

### Rule 3: Advanced Formats
Every 30-question practice batch must contain:
1. **Paragraph-Based Inference Questions (Max 2)**: A 2–3 sentence data-rich premise. Options must test logical deduction rather than rote memory (utilizing qualifiers like *only*, *more than*, *less than*).
2. **Contextual Connect Questions (Max 2)**: Connect a department's core schemes, budget allocations, or targets to their stated policy objectives, target beneficiary groups, or implementation timelines mentioned in the facts.

---

## 2. Core Question Patterns

Every policy practice batch must contain a balanced mix of these standard TNPSC question formats:

### Pattern A: Statement-Evaluation (Target: 30% - 40% of Batch)
Evaluates multiple dimensions of a single government policy, scheme, or allocation.
* **Structure**: Present 2 to 4 numbered statements (1, 2, 3, 4).  For e.g., detailing budget amounts, eligible categories, or target districts.
* **Distractors**: Mix combinations (e.g., "1 and 2 only", "2 and 3 only", "1, 2 and 4", "All the above").

### Pattern B: Match the Following (Target: 15% - 20% of Batch)
Matches lists of related entities (e.g., Schemes $\rightarrow$ Implementing Agencies, Targets $\rightarrow$ Budgets, Regions $\rightarrow$ Focus sectors/milestones).
* **Layout**: Must use our standard 2-column HTML layout:
  ```html
  Match the following:<br><div class='match-container'><div class='match-col-left'>a) Scheme A<br>b) Scheme B<br>c) Scheme C<br>d) Scheme D</div><div class='match-col-right'>1. Agency 1<br>2. Agency 2<br>3. Agency 3<br>4. Agency 4</div></div>
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
Tests singular, crucial policy statistics (e.g., total budget allocation for the department, specific subsidies, or newly announced centers).

---

## 3. Plausible Distractors & Formatting
* **Plausible Distractors**: All incorrect options must use adjacent years, related department names, realistic budget allocations (e.g. ₹5,000 cr instead of ₹5,200 cr), or close statistical percentages to test precision.
* **Option E**: Every question must include `"key": "E", "text_en": "Answer not known", "text_ta": "விடை தெரியவில்லை"`.
* **Bilingual**: Every question, option, and explanation must be fully translated into Tamil.
