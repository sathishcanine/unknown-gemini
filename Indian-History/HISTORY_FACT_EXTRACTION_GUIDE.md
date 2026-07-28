# Indian History Fact Extraction Guide

This guide defines the standard process for performing high-density, duplicate-free fact extraction for any topic in the **Indian History** syllabus. It is tailored to avoid Polity-specific terminology.

---

## 1. History-Specific Fact Targets

When prompting the AI model to extract facts from history materials, explicitly instruct it to focus on the following categories:

* **Dynasties, Kings, and Rulers**: Dynasty founders, prominent kings, reign dates, titles (e.g., *Devaraya*, *Kaviraja*), royal symbols, and royal lineages.
* **Archaeological Sites and Excavations**: Excavated towns (e.g., Harappa, Mohenjodaro, Adichanallur, Keeladi), excavation years, names of archaeologists, and specific objects unearthed (e.g., Great Bath, Dancing Girl, burial urns).
* **Battles, Treaties, and Wars**: Battle names, years, participating rulers/forces, outcomes, and treaties signed (e.g., Battle of Haldighati, Battle of Talikota, Treaty of Purandar).
* **Administrative, Revenue, and Military Systems**: Technical terms for administrative divisions, local bodies, revenue systems, taxes, and military structures (e.g., *Mansabdari*, *Iqta*, *Ayagar system*, *Nayak* rule, *Astadiggajas*).
* **Art, Architecture, and Monuments**: Cave temples, rock-cut architecture, structural temples, building styles (Dravida, Vesara, Nagara), names of builder-kings, and exact locations of monuments.
* **Literature, Authors, and Inscriptions**: Works written by rulers or court poets, language of composition (Sanskrit, Prakrit, Tamil), foreign traveler accounts (e.g., Hiuen Tsang, Fa-Hien, Ibn Battuta), and inscriptions (e.g., Junagarh Rock Inscription, Uttaramerur Inscription, Allahabad Pillar).

---

## 2. Granular Page-by-Page Exhaustive Extraction Method

To ensure maximum density and prevent the LLM from summarizing or missing details, we perform page-by-page extraction:

### Step 1: Text Gathering
Gather page texts from the two targeted sources:
1. **Gurunath History** (`HISTORY_ENGLISH_Gurunath.pdf`)
2. **Suresh History** (`Indian_history_suresh_usable.pdf`)

### Step 2: Page-by-Page Resolution
Rather than partitioning the combined text into a few large chunks, we query the Gemini API page-by-page (text segments of ~1,500 to 2,000 characters).

### Step 3: API Extraction Prompt
Use the exhaustive extraction prompt. Command the LLM to pull out every detail, name, year, and site, outputting at least 8-15 distinct facts per page. The output format must be a JSON array:
```json
[
  {
    "fact_en": "Verifiable fact statement in English",
    "fact_ta": "Verifiable fact statement in Tamil",
    "source": "Gurunath / Suresh / Both",
    "context_en": "Historical context in English",
    "context_ta": "Historical context in Tamil"
  }
]
```

### Step 4: Clean & Merge
* Combine the page-by-page JSON arrays.
* Deduplicate using normalized alphanumeric string comparison in Python.
* Save the final JSON database to `Indian-History/history_facts.json`.
