# TVK-Government Policies Fact Extraction Guide

This guide defines the standard process for performing high-density, duplicate-free fact extraction for topics under **TVK-Government Policies** (leaders, schemes, and policy notes).

It follows the same method used for INM / Chemistry / Indian History.

---

## 1. TVK-Specific Fact Targets

When prompting the AI model to extract facts from TVK materials, explicitly instruct it to focus on the following categories:

* **Leaders & Office-Bearers**: Names, designations (e.g., Chief Minister, Ministers), portfolios, titles, and key statements or announcements.
* **Schemes & Welfare Programs**: Scheme names (Tamil + English), launch dates, objectives, target beneficiaries, eligibility criteria, and benefits / assistance amounts.
* **Budgets, Subsidies & Financial Allocations**: Exact rupee / crore figures, department or scheme-wise allocations, subsidies, and loan waivers.
* **Timelines & Chronology**: Announcement dates, implementation phases, survey years, and deadlines.
* **Departments, Boards & Agencies**: Implementing departments, directorates, corporations, special task forces, and administrative roles.
* **Statistics & Targets**: Beneficiary counts, districts covered, survey results, production / coverage figures, and stated targets.
* **Acts, Rules & Policy Documents**: Named acts, rules, white papers, policy notes, and official orders mentioned in the source.

---

## 2. Granular Page-by-Page Exhaustive Extraction Method

To ensure maximum density and prevent the LLM from summarizing or missing details, we perform page-by-page extraction:

### Step 1: Text Segment Gathering
Gather page texts from the reconstructed usable sources under `Data/TVK-Government-Data/`:

1. **TVK Leaders** — `TVK_Govt_LEADERS_Policy_Notes_1_usable.pdf` (pages `0..14`)
2. **TVK Policies & Schemes** (second topic, later) — combine:
   - `TVK_govt_Policy_Scheme_part_2_usable.pdf`
   - `Tvk_govt_policy_Scheme_part_3_usable.pdf`

Do **not** use the older large scanned PDFs (non-`_usable` files).

### Step 2: Page-by-Page Resolution
Rather than partitioning the combined text into a few large chunks, query the Gemini API **page-by-page**:

* Prefer `page.get_text()` from the usable PDF.
* Fall back to image OCR only if a page has little/no extractable text (&lt; ~80 characters).

### Step 3: API Extraction Prompt
Use an exhaustive extraction prompt. Command the LLM to pull out every detail, name, year, scheme, and amount, outputting at least **8–15 distinct facts per page** when content allows. The output format must be a JSON array:

```json
[
  {
    "fact_en": "Verifiable fact statement in English",
    "fact_ta": "Verifiable fact statement in Tamil",
    "source": "Leaders / SchemesPart2 / SchemesPart3",
    "context_en": "Short policy context in English",
    "context_ta": "Short policy context in Tamil"
  }
]
```

### Step 4: Clean & Merge
* Combine the page-by-page JSON arrays for the topic.
* Deduplicate using normalized alphanumeric string comparison in Python.
* Save the final JSON database to `TVK/tvk_facts.json` (write after each topic completes).

Example shape:

```json
{
  "TVK Leaders": [ /* facts */ ],
  "TVK Policies & Schemes": [ /* facts — later */ ]
}
```

---

## 3. Rules for Highly Valuable, Unique, and Duplicate-Free Facts

To maintain high data quality and avoid low-value or repetitive entries, apply the following strict rules:

1. **Use Usable PDFs Only**: Extract only from `*_usable.pdf` sources. Do not re-OCR the original large scanned PDFs once usable text PDFs exist.
2. **One Topic Mapping Per Source Block**: Map each syllabus topic to a clear page range. For bilingual pages, extract once and instruct Gemini to output **both** English and Tamil facts (do not double-extract the same content as two separate language passes).
3. **Exclude Verbose Explanations**: Instruct the model to focus strictly on concrete entities (scheme names, leader names, dates, amounts, districts, departments, beneficiary groups) and exclude generic commentary, social-media fluff, or conversational descriptions from the PDF chrome.
4. **Atomic Facts**: Each fact must test one specific piece of information (one amount, one date, one eligibility rule, one designation).
5. **Normalized Alphanumeric Matching**: Perform alphanumeric normalization on the English fact string (`re.sub(r'[^a-zA-Z0-9\u0b80-\u0bff]', '', text).lower()`) when running Python-side deduplication to ignore formatting, whitespace, and punctuation differences.
6. **Skip Completed Topics**: If `tvk_facts.json` already has a non-empty list for a topic, skip that topic on re-run.
7. **Rate Limit & Timeout Defense**: Always set a connection timeout (e.g., `timeout=90` seconds) on HTTP requests and limit thread concurrency (e.g., `max_workers=2`) to prevent API latency from causing silent hangs or thread stalls.
8. **API Key from Environment**: Use `GEMINI_API_KEY` from the environment only — never hardcode keys in scripts.

---

## 4. First Extraction Pass (Current Priority)

| Topic | Source PDF | Pages (0-indexed) |
|-------|------------|-------------------|
| `TVK Leaders` | `TVK_Govt_LEADERS_Policy_Notes_1_usable.pdf` | `0..14` |

Command:

```bash
export GEMINI_API_KEY=...
python3 TVK/extract_tvk_facts.py
```

(Script should process only topics that are empty in `tvk_facts.json`; run Leaders first.)
