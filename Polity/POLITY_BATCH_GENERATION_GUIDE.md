# Indian Polity MCQ Batch Generation Guide

This guide is designed for **the User** and **future AI Agents** to ensure consistent, duplicate-free question generation for any topic in the **Indian Polity** syllabus.

---

## 1. What to Ask the AI (User Prompts)

When you return and want to generate new batches for a Polity topic, copy-paste one of these prompts:

### Option A: Generate the Next Batch for an Existing Topic
> "I want to generate **Batch [X]** for the topic **[Topic Name]** in Indian Polity. 
> 1. Read `Polity/POLITY_BATCH_GENERATION_GUIDE.md` for the polity generation rules and guardrails.
> 2. Load `Polity/polity_questions_db.json` and gather all existing questions (both PYQs and practice batches) under the topic '[Topic Name]' to use as exclusions.
> 3. Use the facts in the `Current Affairs : February 2026` or the respective topic key in `Polity/polity_facts.json`.
> 4. Generate 34 questions, prune to 30 (15 Medium, 15 Hard), shuffle, and append to the database."

### Option B: Start a New Polity Topic from Scratch
> "I want to start a new Indian Polity topic: **[Topic Name]**.
> 1. Locate the study files in the `Data/Polity/` directory.
> 2. Search for the relevant chapters/pages.
> 3. Extract the text and run a 4-round deep-dive fact extraction using the **Text-Segment Partitioning Method** to save to `Polity/polity_facts.json`.
> 4. Transcribe this topic's PYQs from `INDIAN POLITY PYQ PDF 2020 - 2025.pdf` and save them to `Polity/polity_questions_db.json` first.
> 5. Let me know when you are ready to generate Batch 1."

---

## 2. Generation Rules for the AI Agent

Every AI agent must follow these strict guidelines for the Indian Polity subject:

### Rule 1: Source of Truth
* Only learn facts from the official study material PDFs in the `Data/Polity/` directory (Class 11/12 Samacheer, Gurunath, Iyachamy, Suresh Polity). **Do not learn facts from the PYQs** (only use PYQs to learn question patterns, wording, and style).

### Rule 2: Complete Exclusion (Zero Duplicates)
* Before calling the API, the agent **must** load `Polity/polity_questions_db.json`, filter by the current `topic`, and pass the English text of all existing questions as a strict exclusion list in the prompt to ensure 100% unique questions.

### Rule 3: Batch Structure
* **Total Final Questions**: Exactly **30 questions**.
* **Difficulty Split**: Exactly **15 Medium** and **15 Hard** questions.
* **Over-provisioning & Pruning**: Generate **34 questions** (17 Medium, 17 Hard) from the API. Calculate a quality score `len(question_en) + len(explanation)` in Python and discard the 2 shortest/weakest questions in each category.

### Rule 4: Plausible Distractors
* Distractors (wrong options) must be highly plausible and closely related to the question fact. 
  - If the correct answer is a year/statistic/name/article, wrong options must be adjacent articles, realistic numbers, or prominent legal cases from the same era/context.

### Rule 5: Universal Advanced Formats
Every 30-question practice batch must contain:
1. **Paragraph-Based Inference Questions (Min 5)**: 2–3 sentence data-rich premise. Options test logical deduction rather than rote memory (utilizing qualifiers like *only*, *more than*, *less than*).
2. **Contextual Connect Questions (Min 4)**: Core historical constitutional concepts hooked to modern contexts (recent Supreme Court judgments, recent amendments, or central/state executive orders).

### Rule 6: Formatting & Shuffling (Strict 4x4 Match Requirement)
* Match-the-following questions must always be a **strict 4x4 matching layout** (exactly 4 items in Column A and exactly 4 items in Column B). Layouts with 2x2 or 3x3 items are strictly prohibited.
* Use the two-column HTML layout:
  `Match the following:<br><div class='match-container'><div class='match-col-left'>a) Item A<br>b) Item B<br>c) Item C<br>d) Item D</div><div class='match-col-right'>1. Match 1<br>2. Match 2<br>3. Match 3<br>4. Match 4</div></div>`
* Option choices must be formatted as combinations, e.g., `a-2, b-1, c-4, d-3` or `A-2, B-1, C-4, D-3`.
* Shuffled once before saving.

### Rule 7: 4-Round Text-Segment Partitioning Fact Extraction
Before generating questions for any new topic, the agent **must** compile the fact database using the **Text-Segment Partitioning Method** to ensure absolutely no facts are missed.

**Crucial Automation Search Step**:
* **Step 1: Automated Comprehensive Multi-Source Search**:
   The agent must proactively and automatically search ALL PDF files in the `Data/Polity/` directory:
   1. `Class_11_Political_Science_English.pdf`
   2. `Class_12_Political_Science_English.pdf`
   3. `Gurunath_INDIAN_POLITY.pdf`
   4. `Iyachamy_INDIAN_POLITY.pdf`
   5. `suresh_a3_polity.pdf`
   
   The search must use a 3-Round Scanning process:
   * **Round 1: Initial Keyword Search**: Query all PDFs using basic bilingual keywords representing the topic (e.g., 'preamble', 'citizenship', 'fundamental rights', 'writs', 'முகப்புரை', 'குடியுரிமை', 'அடிப்படை உரிமைகள்').
   * **Round 2: Expanded Concept & Synonyms Search**: Query using technical terms, articles, and cases (e.g., 'Magna Carta', 'Habeas Corpus', 'Kesavananda Bharati', 'Minerva Mills', 'Article 21', 'Article 32').
   * **Round 3: Chapter-Level Index Verification**: Check index and neighboring pages of matches in the school textbooks to identify complete chapters. Ensure all pages in these chapters are included.

   The agent **must** print and examine the matches, extract all relevant pages, and combine their text into the combined raw text before beginning fact extraction.
* **Step 2: Partition Text**: Split this combined text into **4 equal parts** (Part 1, Part 2, Part 3, and Part 4).
* **Step 3: Sequential Extraction**:
   - **Round 1**: Feed Part 1 to the API and extract **every single** factual statement, article, year, and name.
   - **Round 2**: Feed Part 2 to the API and extract **every single** fact.
   - **Round 3**: Feed Part 3 to the API and extract **every single** fact.
   - **Round 4**: Feed Part 4 to the API and extract **every single** fact.
* **Step 4: Clean & Merge**: Combine the facts from all 4 rounds, remove duplicates, ensure standard TNPSC bilingual translations, and save the final JSON to `Polity/polity_facts.json`.

---

## 3. Pre-Generation Check (Prerequisites Guardrail)

**CRITICAL GUARDRAIL FOR THE AI AGENT**:
If the User asks to generate a practice batch for an Indian Polity topic (whether a new one or an existing one), you **must not** generate any questions until you perform the following verification:

1. **Verify Facts File**: Check if there is an extracted facts JSON entry for the topic in `Polity/polity_facts.json`.
2. **Verify PYQs**: Check if the topic has its Previous Year Questions (PYQs) transcribed and saved in `Polity/polity_questions_db.json` under `"type": "pyq"`.

**If either of these is missing, DO NOT GENERATE the batch.** 
Instead, stop immediately and report the missing prerequisites.

---

## 4. Database Location
* **Database**: `Polity/polity_questions_db.json` (in the workspace folder).
* **Subject Key**: `"Polity"`
* **Topic Key**: `"Constitution of India"` (or the respective topic name).
* **Question Type**: `"pyq"` (transcribed past questions) or `"practice"` (practice batches).
