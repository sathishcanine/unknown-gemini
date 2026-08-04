# Central Government Schemes — Fact Extraction Guide

Subject (app): **Central Government Schemes** / **மத்திய அரசுத் திட்டங்கள்**

Source PDF (English only):  
`Data/Central-Gov-Schemes/Value Addition - Union Government Schemes - Final Print.pdf`

---

## 1. Hierarchy

1. **Subject**: Central Government Schemes
2. **Main Topics (33)**: One per Ministry / NITI Aayog (syllabus topics in the app)
3. **Subtopics**: Individual schemes under each ministry (e.g. PMFBY, PM-KISAN)

---

## 2. Scheme-Specific Fact Targets

When extracting, pull every detail about:

* **Scheme identity**: Full name, acronym, launch / announcement date, completing / sunset date
* **Ministry / Department / Agency**: Implementing ministry, department, regulator, or nodal agency
* **Aim / Objective**: Stated purpose of the scheme
* **Key features**: Premium rates, benefit amounts, coverage %, eligibility rules, DBT, sub-schemes, portals
* **Beneficiaries**: Target groups (farmers, women, SC/ST, MSMEs, etc.)
* **Budgets / Outlays / Targets**: Hectares, clusters, crore amounts, year-wise goals
* **Related acts / missions / replacements**: What it replaced or converges with

---

## 3. Page-by-Page Extraction Method

### Step 1: Text Gathering
Extract text page-by-page from the English Value Addition PDF using PyMuPDF (`fitz`).

### Step 2: Topic Page Map
Use `topics_mapping` in `extract_cgs_facts.py` (0-indexed PDF pages). Boundary pages may contain two ministries — the prompt must keep **only** facts for the active topic.

### Step 3: API Extraction
For each page, call Gemini with an exhaustive bilingual extraction prompt. Output JSON array:

```json
[
  {
    "fact_en": "Verifiable fact statement in English",
    "fact_ta": "Verifiable fact statement in Tamil",
    "scheme": "Short scheme name or acronym (e.g. PM-KISAN)",
    "source": "Vetri IAS Value Addition - Union Government Schemes",
    "context_en": "Brief context in English",
    "context_ta": "Brief context in Tamil"
  }
]
```

### Step 4: Clean & Merge
* Deduplicate by normalized `fact_en`
* Save under topic key in `Central-Gov-Schemes/cgs_facts.json`

---

## 4. Main Topics (33)

1. Ministry of Agriculture & Farmers Welfare  
2. Ministry of Consumer Affairs, Food and Public Distribution  
3. Ministry of Commerce & Industry  
4. Ministry of Chemicals and Fertilisers  
5. Ministry of Corporate Affairs  
6. Ministry of Culture  
7. Ministry of Communications  
8. Ministry of Civil Aviation  
9. Ministry of Development of the North Eastern Region  
10. Ministry of Earth Sciences  
11. Ministry of Education  
12. Ministry of Electronics and Information Technology  
13. Ministry of Environment, Forest and Climate Change  
14. Ministry of Finance  
15. Ministry of Fisheries, Animal Husbandry and Dairying  
16. Ministry of Health & Family Welfare  
17. Ministry of Heavy Industries  
18. Ministry of Home Affairs  
19. Ministry of Housing and Urban Affairs (MOHUA)  
20. Ministry of Jal Shakti  
21. Ministry of Labour & Employment  
22. Ministry of Micro, Small & Medium Enterprises  
23. Ministry of Mines  
24. Ministry of Minority Affairs  
25. Ministry of New and Renewable Energy  
26. NITI Aayog  
27. Ministry of Panchayati Raj  
28. Ministry of Petroleum and Natural Gas  
29. Ministry of Rural Development  
30. Ministry of Skill Development and Entrepreneurship  
31. Ministry of Social Justice and Empowerment  
32. Ministry of Tribal Affairs  
33. Ministry of Women & Child Development  

---

## 5. Run

```bash
# First topic only
python3 Central-Gov-Schemes/extract_cgs_facts.py --topic "Ministry of Agriculture & Farmers Welfare"

# All remaining empty topics
python3 Central-Gov-Schemes/extract_cgs_facts.py
```

Requires `GEMINI_API_KEY` in the environment.
