# Indian National Movement (INM) Fact Extraction Guide

This guide defines the standard process for performing high-density, duplicate-free fact extraction for any topic in the **Indian National Movement (INM)** syllabus.

---

## 1. INM-Specific Fact Targets

When prompting the AI model to extract facts from INM materials, explicitly instruct it to focus on the following categories:

* **Chronology & Timelines**: Key events, years, and dates of the freedom struggle (e.g., Partition of Bengal, Surat Split, Dandi March, Quit India Movement).
* **Leaders & Personalities**: Prominent freedom fighters (e.g., Gandhi, Nehru, Ambedkar, Bose, Kamarajar, Periyar, Rajaji, V.O. Chidambaranar, Bharathiyar), their birth/death years, titles, achievements, and statements.
* **Organizations & Movements**: Political parties, associations, secret societies, and social reform groups (e.g., Indian National Congress, Swadeshi Movement, Home Rule League, Self-Respect Movement, Justice Party, Madras Mahajana Sabha).
* **Newspapers, Journals, & Literature**: Revolutionary and patriotic newspapers, journals, books, pamphlets, and songs (e.g., Swadesamitran, Kesari, Young India, New India, Harijan, writings of Bharathiyar).
* **Acts, Commissions, & Conferences**: British legislative acts, commissions, declarations, pacts, and round table conferences (e.g., Rowlatt Act, Simon Commission, Poona Pact, Cripps Mission, Cabinet Mission).
* **Role of Tamil Nadu in Freedom Struggle**: Events, protests, and contributions specific to Tamil Nadu (e.g., Vellore Revolt, Swadeshi Steam Navigation Company, Neil Statue Satyagraha, Vedaranyam Salt Satyagraha).

---

## 2. Granular Page-by-Page Exhaustive Extraction Method

To ensure maximum density and prevent the LLM from summarizing or missing details, we perform page-by-page extraction:

### Step 1: Text Segment Gathering
Gather page texts from the two reconstructed usable sources:
1. **Suresh INM** (`INM_suresh_A3_usable.pdf`)
2. **TAF INM** (`INM_taf_usable.pdf`)

### Step 2: Page-by-Page Resolution
Rather than partitioning the combined text into a few large chunks, we query the Gemini API page-by-page (text segments of ~1,500 to 2,000 characters).

### Step 3: API Extraction Prompt
Use the exhaustive extraction prompt. Command the LLM to pull out every detail, name, year, and event, outputting at least 8-15 distinct facts per page. The output format must be a JSON array:
```json
[
  {
    "fact_en": "Verifiable fact statement in English",
    "fact_ta": "Verifiable fact statement in Tamil",
    "source": "Suresh / TAF / Both",
    "context_en": "Historical context in English",
    "context_ta": "Historical context in Tamil"
  }
]
```

### Step 4: Clean & Merge
* Combine the page-by-page JSON arrays.
* Deduplicate using normalized alphanumeric string comparison in Python.
* Save the final JSON database to `INM/inm_facts.json`.

---

## 3. Rules for Highly Valuable, Unique, and Duplicate-Free Facts

To maintain high data quality and avoid low-value or repetitive entries, apply the following strict rules:

1. **Map Only One Section in Bilingual Books**: If a source textbook contains identical content translated into both English and Tamil (like the Suresh INM book), **do not extract facts from both sections**. Map only the **English pages** for the topic, and instruct the Gemini model to output the facts in both English and Tamil. This eliminates 100% of semantic near-duplicates.
2. **Exclude Verbose Explanations**: Instruct the model to focus strictly on concrete entities (names of rulers, leaders, explorers, treaties, wars, dates, locations, charters, and currencies) and exclude generic commentary or conversational descriptions.
3. **Normalized Alphanumeric Matching**: Perform alphanumeric normalization on the English fact string (`re.sub(r'[^a-zA-Z0-9\u0b80-\u0bff]', '', text).lower()`) when running Python-side deduplication to ignore formatting, whitespace, and punctuation differences.
4. **Rate Limit & Timeout Defense**: Always set a connection timeout (e.g., `timeout=90` seconds) on HTTP requests and limit thread concurrency (e.g., `max_workers=2`) to prevent API latency from causing silent hangs or thread stalls.

