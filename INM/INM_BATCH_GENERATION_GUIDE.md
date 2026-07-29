# Indian National Movement (INM) MCQ Batch Generation Guide

This guide is designed for **the User** and **future AI Agents** to ensure consistent, duplicate-free question generation for any topic in the **Indian National Movement (INM)** syllabus.

---

## 1. What to Ask the AI (User Prompts)

When you return and want to generate new batches for an INM topic, copy-paste one of these prompts:

### Option A: Generate the Next Batch for an Existing Topic
> "I want to generate **Batch [X]** for the topic **[Topic Name]** in Indian National Movement. 
> 1. Read `INM/INM_BATCH_GENERATION_GUIDE.md` for the INM generation rules and guardrails.
> 2. Load `INM/inm_questions_db.json` and gather all existing questions (both PYQs and practice batches) under the topic '[Topic Name]' to use as exclusions.
> 3. Use the facts in the respective topic key in `INM/inm_facts.json`.
> 4. Generate 34 questions, prune to 30 (15 Medium, 15 Hard), shuffle, and append to the database."

### Option B: Start a New INM Topic from Scratch
> "I want to start a new INM topic: **[Topic Name]**.
> 1. Locate the study files in the `Data/INM-Data/` directory.
> 2. Search for the relevant chapters/pages.
> 3. Extract the text and run a page-by-page fact extraction to save to `INM/inm_facts.json`.
> 4. Transcribe this topic's PYQs from `INM PYQ PDF 2020 -2025.pdf` and save them to `INM/inm_questions_db.json` first.
> 5. Let me know when you are ready to generate Batch 1."

---

## 2. Generation Rules for the AI Agent

Every AI agent must follow these strict guidelines for the INM subject:

### Rule 1: Source of Truth
* Only learn facts from the official study material PDFs in the `Data/INM-Data/` directory (Suresh INM, TAF INM). **Do not learn facts from the PYQs** (only use PYQs to learn question patterns, wording, and style).

### Rule 2: Complete Pool Analysis & Zero Duplicates
* **No Fact Slicing**: For every batch (including Batch 1, Batch 2, and onward), the generator script **must** load and analyze the **entire pool of facts** for that topic in `inm_facts.json`, rather than slicing them into subsets.
* **Strict Question Exclusion**: To guarantee zero duplication, the script loads all existing questions from `inm_questions_db.json` for that topic and passes their English text as a strict exclusion list. The API will choose from the entire fact pool but must craft entirely new questions that do not duplicate the existing ones.

### Rule 3: Batch Structure
* **Total Final Questions**: Exactly **30 questions**.
* **Difficulty Split**: Roughly **15 Medium** and **15 Hard** questions (splits like 17/13, 18/12, 16/14 are fully acceptable).
* **Over-provisioning & Dynamic Selection**:
  * Generate **34 questions** (18 Medium, 16 Hard) from the API.
  * Filter out invalid questions and sort the remaining lists by quality score (`len(question_en) + len(explanation)` descending).
  * Dynamically select the 30 best questions: If there are fewer than 13 Hard questions, take all available Hard questions and make up the remainder from Medium (e.g., 18 Medium / 12 Hard); if there are fewer than 17 Medium, take all available Medium and make up the remainder from Hard; otherwise, select 17 Medium and 13 Hard. This discards the shortest/weakest questions while ensuring a total of 30.

### Rule 4: Plausible Distractors
* Distractors (wrong options) must be highly plausible and closely related to the question fact. 
  - If the correct answer is a year/statistic/name, wrong options must be adjacent years, realistic numbers, or other prominent historical figures/dynasties from the same era/context.

### Rule 5: Universal Advanced Formats
Every 30-question practice batch must contain:
1. **Paragraph-Based Inference Questions (Min 5)**: 2–3 sentence data-rich premise. Options test logical deduction rather than rote memory (utilizing qualifiers like *only*, *more than*, *less than*).
2. **Contextual Connect Questions (Min 4)**: Connect historical systems, acts, treaties, or journals to their stated administrative, cultural, or social objectives.

### Rule 6: Formatting & Shuffling (Strict 4x4 Match Requirement)
* Match-the-following questions must always be a **strict 4x4 matching layout** (exactly 4 items in Column A and exactly 4 items in Column B). Layouts with 2x2 or 3x3 items are strictly prohibited.
* Use the two-column HTML layout:
  `Match the following:<br><div class='match-container'><div class='match-col-left'>a) Item A<br>b) Item B<br>c) Item C<br>d) Item D</div><div class='match-col-right'>1. Match 1<br>2. Match 2<br>3. Match 3<br>4. Match 4</div></div>`
* Option choices must be formatted as combinations, e.g., `a-2, b-1, c-4, d-3` or `A-2, B-1, C-4, D-3`.
* Shuffled once before saving.

---

## 3. Pre-Generation Check (Prerequisites Guardrail)

**CRITICAL GUARDRAIL FOR THE AI AGENT**:
If the User asks to generate a practice batch for an INM topic (whether a new one or an existing one), you **must not** generate any questions until you perform the following verification:

1. **Verify Facts File**: Check if there is an extracted facts JSON entry for the topic in `INM/inm_facts.json`.
2. **Verify PYQs**: Check if the topic has its Previous Year Questions (PYQs) transcribed and saved in `INM/inm_questions_db.json` under `"type": "pyq"`.

**If either of these is missing, DO NOT GENERATE the batch.** 
Instead, stop immediately and report the missing prerequisites.

---

## 4. Database Location
* **Database**: `INM/inm_questions_db.json` (in the workspace folder).
* **Subject Key**: `"INM"`
* **Topic Key**: Respective topic name.
* **Question Type**: `"pyq"` (transcribed past questions) or `"practice"` (practice batches).
