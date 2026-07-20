# Indian Economy MCQ Batch Generation Guide

This guide is designed for **the User** and **future AI Agents** to ensure consistent, duplicate-free question generation for any topic in the **Indian Economy** syllabus.

---

## 1. What to Ask the AI (User Prompts)

When you return and want to generate new batches for an Economy topic, copy-paste one of these prompts:

### Option A: Generate the Next Batch for an Existing Topic
> "I want to generate **Batch [X]** for the topic **[Topic Name]** in Indian Economy. 
> 1. Read `ECONOMY_BATCH_GENERATION_GUIDE.md` for the economy generation rules and guardrails.
> 2. Load `questions_db.json` and gather all existing questions (both PYQs and practice batches) under the topic '[Topic Name]' to use as exclusions.
> 3. Use the facts in `scratch/[topic_name]_facts.json`.
> 4. Generate 34 questions, prune to 30 (15 Medium, 15 Hard), shuffle, and append to the database."

### Option B: Start a New Economy Topic from Scratch
> "I want to start a new Indian Economy topic: **[Topic Name]**.
> 1. Locate the study files in the `Data-Economics/` directory.
> 2. Search for the relevant chapters/pages.
> 3. Extract the text and run a 4-round deep-dive fact extraction using the **Text-Segment Partitioning Method** to save a new `scratch/[topic_name]_facts.json` file.
> 4. Transcribe this topic's PYQs from `INDIAN ECONOMY PYQ PDF 2020 -2025.pdf` and save them to `questions_db.json` first.
> 5. Let me know when you are ready to generate Batch 1."

---

## 2. Generation Rules for the AI Agent

Every AI agent must follow these strict guidelines for the Indian Economy subject:

### Rule 1: Source of Truth
* Only learn facts from the official study material PDFs in the `Data-Economics/` directory (Class 11/12 Samacheer, Gurunath, Suresh Polity). **Do not learn facts from the PYQs** (only use PYQs to learn question patterns, wording, and style).

### Rule 2: Complete Exclusion (Zero Duplicates)
* Before calling the API, the agent **must** load `questions_db.json`, filter by the current `topic`, and pass the English text of all existing questions as a strict exclusion list in the prompt to ensure 100% unique questions.

### Rule 3: Batch Structure
* **Total Final Questions**: Exactly **30 questions**.
* **Difficulty Split**: Exactly **15 Medium** and **15 Hard** questions.
* **Over-provisioning & Pruning**: Generate **34 questions** (17 Medium, 17 Hard) from the API. Calculate a quality score `len(question_en) + len(explanation)` in Python and discard the 2 shortest/weakest questions in each category.

### Rule 4: Plausible Distractors
* Distractors (wrong options) must be highly plausible and closely related to the question fact. 
  - If the correct answer is a year/statistic/name, wrong options must be adjacent years, realistic percentages, or prominent names from the same era/context.

### Rule 5: Universal Advanced Formats
Every 30-question practice batch must contain:
1. **Paragraph-Based Inference Questions (Min 5)**: 2–3 sentence data-rich premise. Options test logical deduction rather than rote memory (utilizing qualifiers like *only*, *more than*, *less than*).
2. **Contextual Connect Questions (Min 4)**: Core historical concepts hooked to modern contexts (recent global summits like G20/Y20/COP, recent government schemes, or NITI Aayog meetings).

### Rule 6: Formatting & Shuffling
* Match-the-following questions must use the two-column HTML layout:
  `Match the following:<br><div class='match-container'><div class='match-col-left'>a) A<br>b) B</div><div class='match-col-right'>1. X<br>2. Y</div></div>`
* Shuffled once before saving.

### Rule 7: 4-Round Text-Segment Partitioning Fact Extraction
Before generating questions for any new topic, the agent **must** compile the fact database using the **Text-Segment Partitioning Method** to ensure absolutely no facts (known or unknown) are missed.

**Crucial Automation Search Step**:
* **Step 1: Automated Comprehensive Multi-Source Search**:
  The agent must proactively and automatically search ALL four PDF files in the `Data-Economics/` directory:
  1. `Class_11_Economics_Tamil_2024_Edition-www.tntextbooks.in.pdf`
  2. `Class_12_Economics_Tamil_2024_Edition-www.tntextbooks.in.pdf`
  3. `Gurunath_Economics_Material_Tamil.pdf`
  4. `suresh_a3_polity_usable.pdf`
  
  The search must use a 3-Round Scanning process:
  * **Round 1: Initial Keyword Search**: Query all 4 PDFs using basic bilingual keywords representing the topic (e.g., 'population', 'poverty', 'employment', 'education', 'health', 'மக்கள் தொகை', 'வறுமை', 'வேலைவாய்ப்பு').
  * **Round 2: Expanded Concept & Synonyms Search**: Query using technical terms, related indicators, and specific schemes (e.g., 'Malthusian', 'demographic transition', 'Lorenz curve', 'Gini coefficient', 'Morris D. Morris', 'Ayushman Bharat', 'MGNREGA', 'SSA', 'RTE', 'மால்தஸ்', 'மக்கள்தொகை வெடிப்பு', 'வறுமைக் கோடு').
  * **Round 3: Chapter-Level Gap Analysis & Index Verification**: Check table of contents and neighboring pages of matches in the school textbooks to identify complete chapters. Ensure all pages in these chapters are included, leaving no gaps.

  The agent **must** print and examine the matches, extract all relevant pages, and combine their text into the combined raw text before beginning fact extraction. The agent must never rely on simple title matches or wait for the user to suggest missing pages or source files.
* **Step 2: Partition Text**: Split this combined text into **4 equal parts** (Part 1, Part 2, Part 3, and Part 4).
3. **Sequential Extraction**:
   - **Round 1**: Feed Part 1 to the API and extract **every single** factual statement, statistic, year, and name (no conceptual filters).
   - **Round 2**: Feed Part 2 to the API and extract **every single** fact.
   - **Round 3**: Feed Part 3 to the API and extract **every single** fact.
   - **Round 4**: Feed Part 4 to the API and extract **every single** fact.
4. **Round 5 (Clean & Merge)**: Combine the facts from all 4 rounds, remove duplicates, ensure standard TNPSC bilingual translations, and save the final JSON to `scratch/[topic_name]_facts.json`.

---

## 3. Pre-Generation Check (Prerequisites Guardrail)

**CRITICAL GUARDRAIL FOR THE AI AGENT**:
If the User asks to generate a practice batch for an Indian Economy topic (whether a new one or an existing one), you **must not** generate any questions until you perform the following verification:

1. **Verify Facts File**: Check if there is an extracted facts JSON file for the topic in the `scratch/` directory (e.g., `scratch/[topic_name]_facts.json`).
2. **Verify PYQs**: Check if the topic has its Previous Year Questions (PYQs) transcribed and saved in `questions_db.json` under `"type": "pyq"`.

**If either of these is missing, DO NOT GENERATE the batch.** 
Instead, stop immediately and report:
* "I cannot generate the batch yet because the following prerequisites are missing:"
* List exactly what is missing (e.g., "The facts have not been extracted from the study material yet", or "The PYQs for this topic have not been transcribed into the database yet").
* Ask the User for permission to perform the text extraction and PYQ transcription first.

---

## 4. Database Location
* **Database**: `questions_db.json` (in the workspace root).
* **Subject Key**: `"Economy"`
* **Topic Key**: `"Planning Commission"` (or the respective topic name).
* **Question Type**: `"pyq"` (transcribed past questions) or `"practice"` (practice batches).
