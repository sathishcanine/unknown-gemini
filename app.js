/* ==========================================================================
   APP CONTROLLER & LOGIC: TNPSC PREP
   ========================================================================== */

// App State
const state = {
  activeScreen: 'screen-home',
  activeSubject: 'Economy',
  activeGroup: 'Group 1',
  activeTopic: null,
  questions: [], // Loaded from questions_db.json
  testHistory: [], // Loaded from LocalStorage
  currentTest: null, // Info of the ongoing test
  textbookMapping: {
    "Nature of Indian Economy": {
      title: "Nature of Indian Economy",
      titleTa: "இந்திய பொருளாதாரத்தின் இயல்பு",
      book: "Class 11 Economics Textbook (11ஆம் வகுப்பு பொருளியல்)",
      chapter: "Chapter 7: Indian Economy (அத்தியாயம் 7: இந்திய பொருளாதாரம்)",
      pages: "Pages 141 - 156",
      focus: "Focus on features of Indian economy (strength & weaknesses), mixed economy concept, and development indicators (GNH, HDI, standard of living)."
    },
    "Planning Commission": {
      title: "Planning Commission",
      titleTa: "திட்டக்குழு",
      book: "Class 11 Economics Textbook (11ஆம் வகுப்பு பொருளியல்) & Suresh Polity",
      chapter: "Chapter 8: Economic Planning (அத்தியாயம் 8: பொருளாதார திட்டமிடல்)",
      pages: "Pages 160 - 172",
      focus: "Focus on the history of the Planning Commission, National Development Council (NDC), and pre-independence economic plans."
    },
    "Five Year Plan": {
      title: "Five Year Plans & Performance",
      titleTa: "ஐந்தாண்டு திட்டங்கள் மற்றும் சாதனைகள்",
      book: "Class 12 Economics Textbook (12ஆம் வகுப்பு பொருளியல்)",
      chapter: "Chapter 11: Economic Development and Planning (அத்தியாயம் 11: பொருளாதார மேம்பாடு மற்றும் திட்டமிடல்)",
      pages: "Pages 290 - 303",
      focus: "Focus on the growth targets, models, actual outcomes, plan holidays, rolling plans, and evaluation of all 12 Five-Year Plans."
    },
    "NITI Aayog": {
      title: "NITI Aayog",
      titleTa: "நிதி ஆயோக்",
      book: "Class 12 Economics Textbook (12ஆம் வகுப்பு பொருளியல்) & Gurunath",
      chapter: "Chapter 11: Economic Development and Planning (அத்தியாயம் 11: பொருளாதார மேம்பாடு மற்றும் திட்டமிடல்) & Gurunath Page 35",
      pages: "Class 12 Page 291 / Gurunath Page 35",
      focus: "Focus on NITI Aayog origin, structure, Governing Council components, think tank functions, cooperative federalism, and differences from the Planning Commission."
    },
    "National Income": {
      title: "National Income",
      titleTa: "தேசிய வருவாய்",
      book: "Class 12 Economics Textbook (12ஆம் வகுப்பு பொருளியல்)",
      chapter: "Chapter 2: National Income (அத்தியாயம் 2: நாட்டு வருமானம்)",
      pages: "Pages 23 - 43",
      focus: "Focus on GDP, GNP, NNP concepts, per capita income equations, measurement methods (Product, Income, Expenditure), and difficulties in calculation."
    },
    "Fiscal Policy": {
      title: "Fiscal Policy",
      titleTa: "நிதிக் கொள்கை",
      book: "Class 12 Economics Textbook (12ஆம் வகுப்பு பொருளியல்)",
      chapter: "Chapter 9: Fiscal Economics (அத்தியாயம் 9: நிதிப் பொருளியல்)",
      pages: "Pages 237 - 244",
      focus: "Focus on Fiscal Policy instruments (Taxation, Public Expenditure, Public Debt, Deficit Financing), academic definitions, and socio-economic objectives."
    },
    "Finance Commission": {
      title: "Finance Commission",
      titleTa: "நிதிக்குழு",
      book: "Class 12 Economics Textbook (12ஆம் வகுப்பு பொருளியல்)",
      chapter: "Chapter 9: Fiscal Economics (அத்தியாயம் 9: நிதிப் பொருளியல்)",
      pages: "Pages 233 - 235",
      focus: "Focus on Finance Commission history, table of chairmen (1st to 15th), Article 280 constitutional provisions, and vertical/horizontal fiscal imbalances."
    },
    "GST": {
      title: "GST",
      titleTa: "சரக்கு மற்றும் சேவை வரி (GST)",
      book: "Class 12 Economics Textbook (12ஆம் வகுப்பு பொருளியல்) & Gurunath",
      chapter: "Chapter 9: Fiscal Economics (அத்தியாயம் 9: நிதிப் பொருளியல்) & Gurunath Page 144",
      pages: "Class 12 Page 220 - 221 / Gurunath Page 144",
      focus: "Focus on Goods and Services Tax (GST) timeline (March 29, 2017 & July 1, 2017), Central vs State taxes subsumed, CGST/SGST/IGST divisions, destination-based rules, VAT vs GST, and technological features."
    },
    "RBI": {
      title: "RBI",
      titleTa: "இந்திய ரிசர்வ் வங்கி (RBI)",
      book: "Class 12 Economics Textbook (12ஆம் வகுப்பு பொருளியல்) & Gurunath",
      chapter: "Chapter 6: Banking (அத்தியாயம் 6: வங்கியியல்) & Gurunath Page 100",
      pages: "Class 12 Page 120 - 128 / Gurunath Page 100",
      focus: "Focus on Reserve Bank of India (RBI) timelines (1934 Act, April 1, 1935 start, Jan 1, 1949 nationalization), the 15 central banking functions, quantitative vs qualitative credit control tools (bank rate, CRR, SLR, repo, reverse repo, moral suasion, rationing), PSS Act 2007, Banking Ombudsman 1995, ARDC 1963, NABARD 1982, and RRBs 1975."
    },
    "Banking Sector": {
      title: "Banking Sector",
      titleTa: "வங்கித் துறை (Banking Sector)",
      book: "Class 11 & Class 12 Economics Textbook (11 & 12ஆம் வகுப்பு பொருளியல்)",
      chapter: "Class 11 Chapter 8: Indian Economy & Class 12 Chapter 6: Banking",
      pages: "Class 11 Pages 213 - 214 / Class 12 Pages 111 - 119 & 130 - 134",
      focus: "Focus on bank nationalization history (July 19, 1969 & 1980 deposits requirements and bank counts), the 4 consolidated public sector bank mergers, commercial banking functions (primary vs secondary), credit creation mechanics (primary vs derived deposits, money multiplier formula), NBFIs, and development banking details (IFCI 1948, ICICI 1955, IDBI 1976, EXIM 1982, SFCs 1951, and SIDCOs)."
    },
    "Monetary Policy": {
      title: "Monetary Policy",
      titleTa: "பணவியல் கொள்கை (Monetary Policy)",
      book: "Class 12 Economics Textbook (12ஆம் வகுப்பு பொருளியல்) & Gurunath",
      chapter: "Chapter 6: Banking (அத்தியாயம் 6: வங்கியியல்) & Gurunath Page 119",
      pages: "Class 12 Pages 134 - 137 / Gurunath Pages 119 - 123",
      focus: "Focus on cheap money vs dear money states (inflation/recession), Milton Friedman (1976 Nobel Prize, Monetary History book), Cassel/Keynes (1936 General Theory book) theories, neutrality of money, and the 6 key objectives of monetary policy."
    },
    "Inflation": {
      title: "Inflation",
      titleTa: "பணவீக்கம் (Inflation)",
      book: "Class 12 Economics Textbook (12ஆம் வகுப்பு பொருளியல்)",
      chapter: "Chapter 5: Monetary Economics (அத்தியாயம் 5: பணவியல் பொருளியல்)",
      pages: "Class 12 Pages 98 - 106",
      focus: "Focus on Keynes' determination equations (n=p(k+rk')), classifications of inflation by speed (creeping <3%, walking 3-9%, running 10-20%, hyper/galloping >20%), Zimbabwe's 2007 hyperinflation, demand-pull/cost-push/credit/deficit causes, wage-price spiral, effects on distribution (debtors/creditors, entrepreneurs, fixed income), deflation, stagflation, and the 4 business cycle phases (boom, recession, depression, recovery)."
    },
    "Source of revenue": {
      title: "Source of revenue",
      titleTa: "வருவாய் ஆதாரங்கள் (Source of Revenue)",
      book: "Class 12 Economics Textbook (12ஆம் வகுப்பு பொருளியல்) & Gurunath",
      chapter: "Chapter 9: Fiscal Economics (அத்தியாயம் 9: நிதிப் பொருளியல்) & Gurunath Page 144",
      pages: "Class 12 Pages 213 - 219 / Gurunath Pages 144 - 153",
      focus: "Focus on public/government revenue definitions, direct vs indirect tax differences, merits/demerits of direct/indirect taxes, Adam Smith's 4 canons of taxation (equity, certainty, convenience, economy), and non-tax revenue components (fees, fines, public sector dividends, special assessments, gifts/grants, escheats)."
    },
    "Resource Sharing": {
      title: "Resource Sharing",
      titleTa: "மத்திய மாநில வளப் பகிர்வு (Resource Sharing)",
      book: "Class 12 Economics Textbook (12ஆம் வகுப்பு பொருளியல்) & Gurunath",
      chapter: "Chapter 9: Fiscal Economics (அத்தியாயம் 9: நிதிப் பொருளியல்) & Gurunath Page 166",
      pages: "Class 12 Pages 230 - 233 / Gurunath Pages 166 - 169",
      focus: "Focus on division of legislative powers (7th Schedule: Union (100), State (61), Concurrent (52) list counts), financial distribution constitutional articles (Articles 268, 269, 270, 271, 272, 275(1), 282), Finance Commission (Article 280) role/milestones (1st, 14th, 15th FC), federal finance principles (independence, uniformity, adequacy, administrative economy, accountability), and fiscal fairness rules."
    },
    "Rural Welfare": {
      title: "Rural Welfare",
      titleTa: "கிராமப்புற நலம் சார்ந்த திட்டங்கள் (Rural Welfare)",
      book: "Class 11 Economics Textbook & Gurunath & Suresh",
      chapter: "Class 11 Chapter 10: Rural Economics & Gurunath Page 36 & Suresh Page 14",
      pages: "Class 11 Pages 261 - 263 / Gurunath Pages 36 - 44 / Suresh Page 14",
      focus: "Focus on rural electrification statistics (99.25% in 2017), rural road length (26.50 lakh km, 13.5% paved), Gilbert Slater's 1918 village study book, DPSP (Articles 36-51) Irish origins and Ambedkar/Granville descriptions, DPSP Articles 40, 41, 43, 43B, 46, 47, early welfare programs (CDP 1952, DPAP 1973), chronological employment schemes (JRY 1989, EAS 1993, SGRY 2001, MGNREGA 2006), self-employment/skill programs (TRYSEM 1979, IRDP 1980, DWCRA 1982, PMRY 1993, SGSY 1999), and infrastructure schemes (REC 1969, HUDCO 1970, PMGSY 2000, Antyodaya Anna Yojana 2000)."
    },
    "Land Reforms": {
      title: "Land Reforms",
      titleTa: "நிலச் சீர்திருத்தங்கள் (Land Reforms)",
      book: "Class 11 Economics Textbook & Gurunath & Suresh",
      chapter: "Class 11 Chapter 8: Indian Economy before and after Independence & Gurunath Page 68 & Suresh Page 61",
      pages: "Class 11 Pages 205 - 207 / Gurunath Page 68 / Suresh Page 61",
      focus: "Focus on British land tenure systems (Zamindari/Landlord, Ryotwari/Owner-cultivator, Mahalwari/Joint-village), Cornwallis 1793 Permanent Settlement Act, 10/11th to government vs 1/11th to Zamindars ratio, Ryotwari 1820 Thomas Munro in Tamil Nadu, Mahalwari village community management, post-independence land reform objectives (cooperative farming, consolidation of holdings, land ceiling laws, and tenancy reforms), Bhoodan movement (Vinoba Bhave 1951), 1st Constitutional Amendment (1951) introducing 9th Schedule and Article 31B, 9th Schedule laws count (13 to 284), Kesavananda Bharati April 24, 1973 cut-off date, and court cases (Golaknath, Kesavananda Bharati, Minerva Mills)."
    },
    "Agriculture": {
      title: "Agriculture",
      titleTa: "வேளாண்மை (Agriculture)",
      book: "Class 11 Economics Textbook & Gurunath & Suresh",
      chapter: "Class 11 Chapter 8 & Chapter 10 & Gurunath Pages 51-61, 71 & Suresh Page 14",
      pages: "Class 11 Pages 210-211, 259-262 / Gurunath Pages 51-61, 71 / Suresh Page 14",
      focus: "Focus on economic contribution of agriculture, Green Revolution (HYV, seeds/fertilizers/chemical pesticide package, output growth), Second Green Revolution (doubling food grain production from 214 million tons in 2006-07 to 400 million tons by 2020), agricultural credit & rural indebtedness, crop patterns, pricing and marketing institutions (NAFED), crop insurance (NAIS, PMFBY), sustainable agriculture (NMSA), and DPSP Article 47 nutrition/health goals."
    },
    "Agriculture S&T": {
      title: "Science & Tech in Agriculture",
      titleTa: "வேளாண்மையில் அறிவியல் மற்றும் தொழில்நுட்பத்தின் பயன்பாடுகள் (Science & Tech in Agriculture)",
      book: "Class 11 & Class 12 Economics & Gurunath & Suresh",
      chapter: "Class 11 Chapter 8 & Class 12 Chapter 8 & Chapter 10 & Gurunath Pages 6, 36, 58, 59 & Suresh Page 14",
      pages: "Class 11 Pages 210-212 / Class 12 Pages 196-198, 265, 272-273 / Gurunath Pages 6, 36, 58, 59 / Suresh Page 14",
      focus: "Focus on agricultural biotechnology (GM crops/BT cotton), tissue culture, High Yielding Varieties Programme (HYVP 1966-67, seeds/NPK fertilizer/chemical pesticide inputs), early technical programs (IADP 1960-61, IAAP 1964-65), micro-irrigation (National Mission for Micro Irrigation - NMMI 2010, drip and sprinkler systems), National Mission for Sustainable Agriculture (NMSA), organic farming goals, environmental impact of toxic fertilizers (DDT, BHC), Seed Balls (விதை பந்து), WTO agreements (TRIPS 20-year patents / 50-year copyrights, Agreement on Agriculture (AoA) subsidy boxes, TRIMS), and DPSP Article 48 (scientific organization of agriculture)."
    },
    "Industrial Policy": {
      title: "Industrial Policy",
      titleTa: "தொழில் கொள்கை (Industrial Policy)",
      book: "Class 11 & Class 12 Economics & Gurunath & Suresh",
      chapter: "Class 11 Chapter 8 & Chapter 9 & Class 12 Chapter 8 & Gurunath Pages 7, 8, 9, 87 & Suresh Page 14",
      pages: "Class 11 Pages 208-210, 212-217, 234-235, 240 / Class 12 Pages 196-198 / Gurunath Pages 7, 8, 9, 87 / Suresh Page 14",
      focus: "Focus on industrial policy resolutions (IPR 1948, 1956, 1977, 1980, 1991), mixed economy goals, Shyama Prasad Mukherjee, 1956 schedules (A, B, C) and socialistic pattern of society, Morarji Desai Janata Gov 1977 Gandhian model and District Industries Centres (DIC), WTO agreements (TRIPS, GATS, TRIMS, MFA), LPG (Liberalisation, Privatisation, Globalisation), delicensing, disinvestment (பங்குவிலகல்), core large-scale industries history (Iron & Steel Kulti, Jute Rishra 1855, Paper Serampore 1812, Silk global ranking, Digboi first oil well 1889), MSME investment classifications (Micro <₹25L, Small ₹25L-₹5C, Medium ₹5C-₹10C), Special Economic Zones (SEZ) objectives, and DPSP Article 39(b)(c) concentration of wealth."
    },
    "Human Development Index": {
      title: "Human Development Index",
      titleTa: "மனித வள மேம்பாட்டுக் குறியீடு (Human Development Index)",
      book: "Class 11 & Class 12 Economics & Gurunath",
      chapter: "Class 11 Chapter 7 & Chapter 8 & Class 12 Chapter 2 & Chapter 11 & Gurunath Pages 9, 87, 88",
      pages: "Class 11 Pages 174, 224-225 / Class 12 Pages 43, 47 / Gurunath Pages 9, 87, 88",
      focus: "Focus on Human Development Index (HDI) definition, parameters (longevity/life expectancy, education/literacy, per capita income), UNDP global reports since 1990, Mahbub ul Haq and Amartya Sen pioneers, HDI scale classifications (Low 0-0.49, Medium 0.50-0.79, High 0.80-1.0), India's HDI progress (0.302 in 1981 to 0.472 in 2011), India's ranking in global reports (131st in 2016), Kerala 1st vs Bihar last in India, Indian Planning Commission National Human Development Report in 2001, Physical Quality of Life Index (PQLI) created by Morris D. Morris in 1979 measuring infant mortality, life expectancy, and basic literacy (excluding income), Gross National Happiness Index (GNHI) coined in 1972 by Bhutan's 4th King Jigme Singye Wangchuck with its 4 pillars (sustainable development, environmental conservation, cultural promotion, and good governance), and indicators pioneers Harbison and Myers."
    },
    "International Organization": {
      title: "International Organization",
      titleTa: "பன்னாட்டு அமைப்புகள் (International Organization)",
      book: "Class 12 Economics & Gurunath",
      chapter: "Class 12 Chapter 8 & Gurunath Pages 31-34",
      pages: "Class 12 Pages 186-211 / Gurunath Pages 31-34",
      focus: "Focus on International Economic Organisations: IMF (Washington D.C. 1945, Bretton Woods, SDR/Paper Gold 1969, currency basket, World Economic Outlook), World Bank/IBRD (Washington D.C. 1945, World Bank Group IBRD, IDA Soft Loan Window, IFC 1956, MIGA 1988, ICSID 1966 - India NOT a member), WTO (Geneva 1995, replaced GATT 1948, Marrakesh Agreement, TRIPS, TRIMS, GATS, AoA), UNCTAD (1964), regional organizations: SAARC (Kathmandu 1985, member nations, SAFTA), BRICS (2009 first summit, 2010 South Africa added, NDB Shanghai, member nations), ASEAN (Jakarta 1967, Bangkok Declaration, member nations, AFTA), and Asian Development Bank (ADB Manila 1966)."
    },
    "Social Problem : Population": {
      title: "Social Problem : Population",
      titleTa: "சமூகப் பிரச்சினைகள் : மக்கள் தொகை (Social Problem : Population)",
      book: "Class 11 & Class 12 Economics & Gurunath & Suresh",
      chapter: "Class 11 Chapter 7 & Chapter 11 & Class 12 Chapter 11 & Gurunath",
      pages: "Class 11 Pages 176-177, 278-279, 294-295 / Class 12 Pages 283 / Gurunath Pages 9, 87",
      focus: "Focus on population growth indicators, demographic transition theory (3 phases, population explosion), birth rate, death rate, growth rate, population density (TN 555 vs national 382), gender ratio (995 overall, 946 for ages 0-6 in TN), highest and lowest gender ratio districts (Nilgiris/Kanyakumari vs Theni/Dharmapuri), child mortality rate, IMR (17 in 2016) and MMR (79 in 2016) in Tamil Nadu, and Malthusian theory of population."
    },
    "Social Problem : Poverty": {
      title: "Social Problem : Poverty",
      titleTa: "சமூகப் பிரச்சினைகள் : வறுமை (Social Problem : Poverty)",
      book: "Class 11 & Class 12 Economics & Gurunath & Suresh",
      chapter: "Class 11 Chapter 7 & Chapter 10 & Class 12 Chapter 11 & Gurunath Pages 22-26 & Suresh Page 14",
      pages: "Class 11 Pages 179, 248-249 / Class 12 Pages 281-282 / Gurunath Pages 22-26 / Suresh Page 14",
      focus: "Focus on definitions of poverty, rural poverty rates (54.10% in 2009-10), national poverty rates (33.80% in 2009-10), underprivileged groups poverty rate (80% in 2005), 22 crore people below poverty line in 2015, Malcolm Darling's quote ('born in debt, lives in debt...'), Schumacher's 'Small is Beautiful' (Dual Poisoning), Ragnar Nurkse's Vicious Cycle of Poverty, poverty measurement committees (Alagh, Lakdawala, Tendulkar, Rangarajan), AIDIS study (organized credit decrease from 66.3% to 57.1%), and poverty alleviation schemes (20-Point Programme, Food for Work, IRDP, NREP, RLEGP, JRY, Bharat Nirman, NFSA)."
    },
    "Social Problem : Employment": {
      title: "Social Problem : Employment",
      titleTa: "சமூகப் பிரச்சினைகள் : வேலைவாய்ப்பு மற்றும் வேலையின்மை (Social Problem : Employment)",
      book: "Class 11 & Class 12 Economics & Gurunath & Suresh",
      chapter: "Class 11 Chapter 7 & Chapter 10 & Class 12 Chapter 3 & Gurunath Pages 22-26 & Suresh Page 14",
      pages: "Class 11 Pages 179, 249-251 / Class 12 Pages 50-52 / Gurunath Pages 22-26 / Suresh Page 14",
      focus: "Focus on unemployment types (cyclical, seasonal, frictional, structural, disguised, open, voluntary vs involuntary), disguised unemployment estimation (25%-30% in rural areas), Agricultural Labour Enquiry underemployment stat (84% underemployed, 82 idle days/year), Say's Law of Markets vs Keynesian Theory of Income and Employment, unemployment rates (rural 7.8%, urban 10.1%, national 8.5% in Oct 2016), MGNREGA (2006) details, and labour laws (Minimum Wages Act 1948, Bonded Labour System Abolition Act 1976)."
    },
    "Social Problem : Education": {
      title: "Social Problem : Education",
      titleTa: "சமூகப் பிரச்சினைகள் : கல்வி (Social Problem : Education)",
      book: "Class 11 Economics & Gurunath & Suresh",
      chapter: "Class 11 Chapter 7 & Chapter 10 & Chapter 11 & Gurunath Pages 86-87",
      pages: "Class 11 Pages 180-181, 253, 280, 289-290 / Gurunath Pages 86-87",
      focus: "Focus on educational infrastructure, Gross Enrollment Ratio (GER) in higher education in Tamil Nadu (46.9% in 2016-17) vs national average (25.2%), Tamil Nadu's share of public sector bank educational loans (20.8% - highest in India), literacy rate in Tamil Nadu (80.33% - male 86.81%, female 73.86%), highest/lowest literacy districts (Kanyakumari vs Dharmapuri), Right to Education (RTE) provisions, Samacheer Kalvi (2010), and Sarva Shiksha Abhiyan (SSA)."
    },
    "Social Problem : Health": {
      title: "Social Problem : Health",
      titleTa: "சமூகப் பிரச்சினைகள் : சுகாதாரம் (Social Problem : Health)",
      book: "Class 11 Economics & Gurunath & Suresh",
      chapter: "Class 11 Chapter 7 & Chapter 10 & Chapter 11 & Gurunath Pages 86-87",
      pages: "Class 11 Pages 181-182, 254-255, 279, 290-291 / Gurunath Pages 86-87",
      focus: "Focus on health infrastructure (three-tier system), medical tourism and Chennai as 'Medical Capital of India', child mortality rate, IMR and MMR in Tamil Nadu, Cradle Baby Scheme (1992), Mid-day Meal Scheme (1956 - Kamarajar), and ICDS nutrition indices."
    },
    "Constitution of India": {
      title: "Constitution of India",
      titleTa: "இந்திய அரசியலமைப்பு (Constitution of India)",
      book: "Class 12 Political Science Textbook & Gurunath Polity & Suresh Polity",
      chapter: "Class 12 Chapter 1: Constitution of India & Gurunath Chapter 1",
      pages: "Class 12 Pages 1-24 / Gurunath Pages 3-20",
      focus: "Focus on historical background of the Constitution, Regulating Act 1773, Charter Acts, Government of India Acts (1858, 1919, 1935), Cabinet Mission Plan 1946, Constitution Assembly composition and committees (Drafting Committee under Ambedkar), adoption date (Nov 26, 1949) and enforcement date (Jan 26, 1950)."
    },
    "Preamble": {
      title: "Preamble",
      titleTa: "முகப்புரை (Preamble)",
      book: "Class 12 Political Science Textbook & Gurunath Polity & Iyachamy Polity",
      chapter: "Class 12 Chapter 1 & Gurunath Chapter 2",
      pages: "Class 12 Pages 25-30 / Gurunath Pages 21-35",
      focus: "Focus on Preamble text, Objective Resolution by Jawaharlal Nehru (adopted Jan 22, 1947), key descriptors: Sovereign, Socialist, Secular, Democratic, Republic, Justice, Liberty, Equality, Fraternity, and the 42nd Constitutional Amendment Act 1976 (added Socialist, Secular, Integrity)."
    },
    "Salient Features of Constitution": {
      title: "Salient Features of Constitution",
      titleTa: "அரசியலமைப்பின் முக்கிய கூறுகள் (Salient Features of Constitution)",
      book: "Class 12 Political Science Textbook & Gurunath Polity & Suresh Polity",
      chapter: "Class 12 Chapter 1 & Gurunath Chapter 3",
      pages: "Class 12 Pages 31-40 / Gurunath Pages 36-43",
      focus: "Focus on salient features of the Indian Constitution: longest written constitution, mixture of rigidity and flexibility, federal system with unitary bias, parliamentary form of government, independent judiciary, single citizenship, emergency provisions, and sources borrowed from other constitutions (UK, USA, Ireland, Canada, Australia, Germany, USSR, France, South Africa)."
    },
    "Union, States & Union Territories": {
      title: "Union, States & Union Territories",
      titleTa: "ஒன்றியம், மாநிலங்கள் மற்றும் யூனியன் பிரதேசங்கள் (Union, States & UTs)",
      book: "Class 12 Political Science Textbook & Gurunath Polity",
      chapter: "Class 12 Chapter 2 & Gurunath Chapter 4",
      pages: "Class 12 Pages 44-55 / Gurunath Pages 44-55",
      focus: "Focus on Part I (Articles 1-4) of the Constitution, Article 1 (India, that is Bharat, shall be a Union of States), Parliament's power to admit new states (Article 2) and alter boundaries/names (Article 3), reorganisation committees (Dhar Commission 1948, JVP Committee 1948, Fazl Ali State Reorganisation Commission 1953, State Reorganisation Act 1956), creation of linguistic states (Andhra Pradesh as first in 1953), and timelines of state formation."
    },
    "Citizenship": {
      title: "Citizenship",
      titleTa: "குடியுரிமை (Citizenship)",
      book: "Class 12 Political Science Textbook & Gurunath Polity & Iyachamy",
      chapter: "Class 12 Chapter 1 & Gurunath Chapter 5",
      pages: "Class 12 Pages 56-62 / Gurunath Pages 56-67",
      focus: "Focus on Part II (Articles 5-11) of the Constitution, acquisition of citizenship under Citizenship Act 1955 (Birth, Descent, Registration, Naturalisation, Incorporation of territory), loss of citizenship (Renunciation, Termination, Deprivation), Single Citizenship concept, and amendments to the Citizenship Act."
    },
    "Fundamental Rights": {
      title: "Fundamental Rights",
      titleTa: "அடிப்படை உரிமைகள் (Fundamental Rights)",
      book: "Class 12 Political Science Textbook & Gurunath Polity",
      chapter: "Class 12 Chapter 1 & Gurunath Chapter 6",
      pages: "Class 12 Pages 68-100 / Gurunath Pages 68-105",
      focus: "Focus on Part III (Articles 12-35) of the Constitution, source (USA Bill of Rights), Magna Carta of India, six Fundamental Rights: Right to Equality (Arts 14-18), Right to Freedom (Arts 19-22), Right against Exploitation (Arts 23-24), Right to Freedom of Religion (Arts 25-28), Cultural & Educational Rights (Arts 29-30), Right to Constitutional Remedies (Art 32 - 'Heart and Soul' of the Constitution), Writs (Habeas Corpus, Mandamus, Prohibition, Certiorari, Quo Warranto), and suspension of rights during emergency (Article 19 auto-suspends, Articles 20 and 21 CANNOT be suspended)."
    },
    "Current Affairs : January 2026": {
      title: "Current Affairs : January 2026",
      titleTa: "நடப்பு நிகழ்வுகள் : ஜனவரி 2026",
      book: "Zero Current affairs - January 2026 PDF",
      chapter: "January 2026 Compilations",
      pages: "Pages 1 - 18",
      focus: "Focus on January 2026 national and state events, including Supreme Court menstrual health ruling under Article 21, Tamil Nadu's first-place electronics export metrics, the 2025-26 Economic Survey growth projections, ISRO EOS-N1 launch details, and India-EU FTA."
    },
    "Current Affairs : February 2026": {
      title: "Current Affairs : February 2026",
      titleTa: "நடப்பு நிகழ்வுகள் : பிப்ரவரி 2026",
      book: "Zero Current affairs - February 2026 PDF",
      chapter: "February 2026 Compilations",
      pages: "Pages 1 - 12",
      focus: "Focus on February 2026 national, state, and international events, appointments, reports, and summits."
    },
    "Current Affairs : March 2026": {
      title: "Current Affairs : March 2026",
      titleTa: "நடப்பு நிகழ்வுகள் : மார்ச் 2026",
      book: "Zero Current affairs - March 2026 PDF",
      chapter: "March 2026 Compilations",
      pages: "Pages 1 - 12",
      focus: "Focus on March 2026 national, state, and international events, appointments, reports, and summits."
    },
    "Current Affairs : April 2026": {
      title: "Current Affairs : April 2026",
      titleTa: "நடப்பு நிகழ்வுகள் : ஏப்ரல் 2026",
      book: "Zero Current affairs - April 2026 PDF",
      chapter: "April 2026 Compilations",
      pages: "Pages 1 - 12",
      focus: "Focus on April 2026 national, state, and international events, appointments, reports, and summits."
    },
    "Current Affairs : June 2026": {
      title: "Current Affairs : June 2026",
      titleTa: "நடப்பு நிகழ்வுகள் : ஜூன் 2026",
      book: "Zero Current affairs - June 2026 PDF",
      chapter: "June 2026 Compilations",
      pages: "Pages 1 - 21",
      focus: "Focus on June 2026 national, state, and international events, appointments, reports, and summits."
    }
  }
};

// DOM Elements
const DOM = {
  themeToggle: document.getElementById('theme-toggle'),
  statusTime: document.getElementById('status-time'),
  headerGroupDisplay: document.getElementById('header-group-display'),
  screenContainer: document.getElementById('screen-container'),
  
  // Navigation Tabs
  tabs: {
    home: document.getElementById('tab-home'),
    syllabus: document.getElementById('tab-syllabus'),
    advisor: document.getElementById('tab-advisor')
  },
  
  // Screens
  screens: {
    home: document.getElementById('screen-home'),
    syllabus: document.getElementById('screen-syllabus'),
    topicDetail: document.getElementById('screen-topic-detail'),
    quiz: document.getElementById('screen-quiz'),
    results: document.getElementById('screen-results'),
    advisor: document.getElementById('screen-advisor')
  },
  
  // Home Screen Elements
  groupBtns: document.querySelectorAll('.segment-btn'),
  weaknessBanner: document.getElementById('weakness-banner'),
  weaknessBannerText: document.getElementById('weakness-banner-text'),
  weaknessBannerAction: document.getElementById('weakness-banner-action'),
  masteryPercent: document.getElementById('mastery-percent'),
  masteryProgressFill: document.getElementById('mastery-progress-fill'),
  statsTotalTests: document.getElementById('stats-total-tests'),
  statsCorrectRatio: document.getElementById('stats-correct-ratio'),
  statsAvgAccuracy: document.getElementById('stats-avg-accuracy'),
  subjectCardEconomics: document.getElementById('subject-card-economics'),
  subjectEconProgressPct: document.getElementById('subject-econ-progress-pct'),
  subjectEconProgressFill: document.getElementById('subject-econ-progress-fill'),
  subjectEconQuestionsCount: document.getElementById('subject-econ-questions-count'),
  subjectCardCurrentAffairs: document.getElementById('subject-card-current-affairs'),
  subjectCaProgressPct: document.getElementById('subject-ca-progress-pct'),
  subjectCaProgressFill: document.getElementById('subject-ca-progress-fill'),
  subjectCaQuestionsCount: document.getElementById('subject-ca-questions-count'),
  subjectCardPolity: document.getElementById('subject-card-polity'),
  subjectPolityProgressPct: document.getElementById('subject-polity-progress-pct'),
  subjectPolityProgressFill: document.getElementById('subject-polity-progress-fill'),
  subjectPolityQuestionsCount: document.getElementById('subject-polity-questions-count'),
  
  // Syllabus Screen Elements
  topicsContainer: document.getElementById('topics-container'),
  btnToHome: document.querySelectorAll('.btn-to-home'),
  
  // Topic Detail Screen Elements
  topicDetailTitle: document.getElementById('topic-detail-title'),
  topicDetailPyqCount: document.getElementById('topic-detail-pyq-count'),
  topicDetailBatchesContainer: document.getElementById('topic-detail-batches-container'),
  btnBackToSyllabus: document.getElementById('btn-back-to-syllabus'),
  btnStartPyq: document.getElementById('btn-start-pyq'),
  
  // Quiz Screen Elements
  quizTopicDisplay: document.getElementById('quiz-topic-display'),
  quizTimerDisplay: document.getElementById('quiz-timer-display'),
  quizProgressText: document.getElementById('quiz-progress-text'),
  quizProgressBarFill: document.getElementById('quiz-progress-bar-fill'),
  quizQuestionEn: document.getElementById('quiz-question-en'),
  quizQuestionTa: document.getElementById('quiz-question-ta'),
  quizOptionsContainer: document.getElementById('quiz-options-container'),
  quizPrevBtn: document.getElementById('quiz-prev-btn'),
  quizNextBtn: document.getElementById('quiz-next-btn'),
  quizQuitBtn: document.getElementById('quiz-quit-btn'),
  
  // Results Screen Elements
  resultsTopicDisplay: document.getElementById('results-topic-display'),
  resultsScoreValue: document.getElementById('results-score-value'),
  resultsAccuracyPct: document.getElementById('results-accuracy-pct'),
  resultsFeedbackMessage: document.getElementById('results-feedback-message'),
  resultsCorrectCount: document.getElementById('results-correct-count'),
  resultsWrongCount: document.getElementById('results-wrong-count'),
  resultsTimeTaken: document.getElementById('results-time-taken'),
  resultsReviewContainer: document.getElementById('results-review-container'),
  resultsBtnToAdvisor: document.getElementById('results-btn-to-advisor'),
  resultsDasharray: document.getElementById('results-dasharray'),
  
  // Advisor Screen Elements
  advisorSummaryText: document.getElementById('advisor-summary-text'),
  weaknessReviewCta: document.getElementById('weakness-review-cta'),
  weaknessReviewDescription: document.getElementById('weakness-review-description'),
  advisorLaunchReviewBtn: document.getElementById('advisor-launch-review-btn'),
  advisorRecommendationsList: document.getElementById('advisor-recommendations-list')
};

// ==========================================================================
// INITIALIZATION
// ==========================================================================
document.addEventListener('DOMContentLoaded', () => {
  initClock();
  initTheme();
  loadData();
  setupEventListeners();
});

// Real-time status bar clock
function initClock() {
  const updateClock = () => {
    const now = new Date();
    let hours = now.getHours();
    let minutes = now.getMinutes();
    hours = hours < 10 ? '0' + hours : hours;
    minutes = minutes < 10 ? '0' + minutes : minutes;
    DOM.statusTime.textContent = `${hours}:${minutes}`;
  };
  updateClock();
  setInterval(updateClock, 30000);
}

// Light/Dark Theme toggle logic
function initTheme() {
  const savedTheme = localStorage.getItem('tnpsc_theme') || 'dark';
  if (savedTheme === 'light') {
    document.body.classList.remove('dark-theme');
    document.body.classList.add('light-theme');
  } else {
    document.body.classList.add('dark-theme');
    document.body.classList.remove('light-theme');
  }
}

// Setup Event Listeners
function setupEventListeners() {
  // Theme Toggle click
  DOM.themeToggle.addEventListener('click', () => {
    const isDark = document.body.classList.toggle('dark-theme');
    document.body.classList.toggle('light-theme', !isDark);
    localStorage.setItem('tnpsc_theme', isDark ? 'dark' : 'light');
  });

  // Group selection (Group 1, 2, 4)
  DOM.groupBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      DOM.groupBtns.forEach(b => b.classList.remove('active'));
      e.target.classList.add('active');
      
      state.activeGroup = e.target.getAttribute('data-group');
      DOM.headerGroupDisplay.textContent = `${state.activeGroup} Prep`;
      
      // Update UI matching new group filter
      updateDashboardStats();
      renderSyllabusTopics();
    });
  });

  // Navigation tab bar clicks
  Object.keys(DOM.tabs).forEach(tabKey => {
    DOM.tabs[tabKey].addEventListener('click', (e) => {
      // Find button closest to clicked target
      const btn = e.target.closest('.nav-tab');
      if (!btn) return;
      
      const targetScreenId = btn.getAttribute('data-screen');
      navigateTo(targetScreenId);
    });
  });

  // Back to dashboard buttons
  DOM.btnToHome.forEach(btn => {
    btn.addEventListener('click', () => {
      navigateTo('screen-home');
    });
  });

  // Subject Economics Card click -> navigates to syllabus view
  DOM.subjectCardEconomics.addEventListener('click', () => {
    state.activeSubject = 'Economy';
    navigateTo('screen-syllabus');
  });

  // Subject Current Affairs Card click -> navigates to syllabus view
  DOM.subjectCardCurrentAffairs.addEventListener('click', () => {
    state.activeSubject = 'Current Affairs';
    navigateTo('screen-syllabus');
  });

  // Subject Polity Card click -> navigates to syllabus view
  DOM.subjectCardPolity.addEventListener('click', () => {
    state.activeSubject = 'Polity';
    navigateTo('screen-syllabus');
  });

  // Topic Detail Navigation Event Listeners
  DOM.btnBackToSyllabus.addEventListener('click', () => {
    navigateTo('screen-syllabus');
  });

  DOM.btnStartPyq.addEventListener('click', () => {
    if (state.activeTopic) {
      startQuiz(state.activeTopic, "pyq");
    }
  });

  // Quiz Navigation Button Clicks
  DOM.quizPrevBtn.addEventListener('click', () => navigateQuizQuestion(-1));
  DOM.quizNextBtn.addEventListener('click', () => navigateQuizQuestion(1));
  DOM.quizQuitBtn.addEventListener('click', quitQuiz);

  // Results to Advisor button
  DOM.resultsBtnToAdvisor.addEventListener('click', () => {
    navigateTo('screen-advisor');
  });

  // Weakness Review launch from Advisor
  DOM.advisorLaunchReviewBtn.addEventListener('click', () => {
    startWeaknessReviewQuiz();
  });

  // Weakness Banner review launch
  DOM.weaknessBannerAction.addEventListener('click', () => {
    navigateTo('screen-advisor');
    // Scroll to recommendations list
    DOM.advisorRecommendationsList.scrollIntoView({ behavior: 'smooth' });
  });
}

// Navigate between screens
function navigateTo(screenId) {
  // Save current active screen
  state.activeScreen = screenId;
  
  // Update Tab Bar Active States
  Object.keys(DOM.tabs).forEach(tabKey => {
    const tab = DOM.tabs[tabKey];
    const target = tab.getAttribute('data-screen');
    tab.classList.toggle('active', target === screenId);
  });

  // Update Screens Active CSS class
  Object.keys(DOM.screens).forEach(screenKey => {
    const screen = DOM.screens[screenKey];
    if (screen.id === screenId) {
      screen.classList.add('active');
    } else {
      screen.classList.remove('active');
    }
  });

  // Custom UI triggers on navigation
  if (screenId === 'screen-home') {
    updateDashboardStats();
  } else if (screenId === 'screen-syllabus') {
    renderSyllabusTopics();
  } else if (screenId === 'screen-topic-detail') {
    renderTopicDetailScreen();
  } else if (screenId === 'screen-advisor') {
    updateAdvisorScreen();
  }
}

// Load Data from local JSON and LocalStorage
async function loadData() {
  try {
    // 1. Fetch Economics, Current Affairs, and Polity databases
    const resEcon = await fetch('Economic/economics_questions_db.json?v=' + Date.now());
    const resCA = await fetch('Current-affairs/current_affairs_questions_db.json?v=' + Date.now());
    const resPolity = await fetch('Polity/polity_questions_db.json?v=' + Date.now());
    if (!resEcon.ok || !resCA.ok || !resPolity.ok) throw new Error('Failed to load questions database');
    
    const econQs = await resEcon.json();
    const caQs = await resCA.json();
    const polityQs = await resPolity.json();
    state.questions = [...econQs, ...caQs, ...polityQs];
    
    // 2. Load History from LocalStorage
    const storedHistory = localStorage.getItem('tnpsc_test_history');
    if (storedHistory) {
      state.testHistory = JSON.parse(storedHistory);
    }
    
    // 3. Update UI
    updateDashboardStats();
    
  } catch (err) {
    console.error('Error loading data: ', err);
    // Fallback Mock Questions in case of local network issue
    state.questions = getFallbackQuestions();
    state.testHistory = [];
    updateDashboardStats();
  }
}

// ==========================================================================
// STATS & METRICS ENGINE
// ==========================================================================
function updateDashboardStats() {
  const history = state.testHistory;
  
  // Filter questions by active subject and active Group
  const econQuestions = getFilteredQuestions("Economy");
  const caQuestions = getFilteredQuestions("Current Affairs");
  const polityQuestions = getFilteredQuestions("Polity");
  
  // Calc totals
  const totalTests = history.length;
  DOM.statsTotalTests.textContent = totalTests;
  
  // Update available questions counts
  DOM.subjectEconQuestionsCount.textContent = `${econQuestions.length} Questions Available`;
  DOM.subjectCaQuestionsCount.textContent = `${caQuestions.length} Questions Available`;
  DOM.subjectPolityQuestionsCount.textContent = `${polityQuestions.length} Questions Available`;
  
  if (totalTests === 0) {
    DOM.statsCorrectRatio.textContent = "0/0";
    DOM.statsAvgAccuracy.textContent = "0%";
    DOM.masteryPercent.textContent = "0%";
    DOM.masteryProgressFill.style.width = "0%";
    
    DOM.subjectEconProgressPct.textContent = "0%";
    DOM.subjectEconProgressFill.style.width = "0%";
    DOM.subjectCaProgressPct.textContent = "0%";
    DOM.subjectCaProgressFill.style.width = "0%";
    DOM.subjectPolityProgressPct.textContent = "0%";
    DOM.subjectPolityProgressFill.style.width = "0%";
    DOM.weaknessBanner.classList.add('d-none');
    return;
  }
  
  let totalCorrect = 0;
  let totalSolved = 0;
  let accuracySum = 0;
  
  history.forEach(session => {
    totalCorrect += session.correctCount;
    totalSolved += session.totalCount;
    accuracySum += (session.correctCount / session.totalCount);
  });
  
  DOM.statsCorrectRatio.textContent = `${totalCorrect}/${totalSolved}`;
  const avgAccuracy = Math.round((totalCorrect / totalSolved) * 100);
  DOM.statsAvgAccuracy.textContent = `${avgAccuracy}%`;
  
  // Subject progress calculation
  // Progress pct represents: (Number of distinct questions solved with correct answer / Total available questions)
  const correctlySolvedIds = new Set();
  history.forEach(session => {
    Object.keys(session.answers).forEach(qIndexStr => {
      const qIndex = parseInt(qIndexStr);
      const question = session.questions[qIndex];
      const selected = session.answers[qIndex];
      if (question && selected === question.correct_option) {
        // Unique ID based on question text hash
        correctlySolvedIds.add(question.question_en);
      }
    });
  });
  
  // 1. Economy Progress
  const econSolved = Array.from(correctlySolvedIds).filter(qText => 
    econQuestions.some(q => q.question_en === qText)
  ).length;
  const econProgressPct = econQuestions.length > 0 ? Math.round((econSolved / econQuestions.length) * 100) : 0;
  DOM.subjectEconProgressPct.textContent = `${econProgressPct}%`;
  DOM.subjectEconProgressFill.style.width = `${econProgressPct}%`;
  
  // 2. Current Affairs Progress
  const caSolved = Array.from(correctlySolvedIds).filter(qText => 
    caQuestions.some(q => q.question_en === qText)
  ).length;
  const caProgressPct = caQuestions.length > 0 ? Math.round((caSolved / caQuestions.length) * 100) : 0;
  DOM.subjectCaProgressPct.textContent = `${caProgressPct}%`;
  DOM.subjectCaProgressFill.style.width = `${caProgressPct}%`;
  
  // 3. Polity Progress
  const politySolved = Array.from(correctlySolvedIds).filter(qText => 
    polityQuestions.some(q => q.question_en === qText)
  ).length;
  const polityProgressPct = polityQuestions.length > 0 ? Math.round((politySolved / polityQuestions.length) * 100) : 0;
  DOM.subjectPolityProgressPct.textContent = `${polityProgressPct}%`;
  DOM.subjectPolityProgressFill.style.width = `${polityProgressPct}%`;
  
  // Overall mastery is linked to average accuracy for now
  DOM.masteryPercent.textContent = `${avgAccuracy}%`;
  DOM.masteryProgressFill.style.width = `${avgAccuracy}%`;
  
  // Check for critical weakness to display dashboard alert banner
  const weakness = getTopicWeaknessReport();
  const critical = weakness.find(w => w.status === 'critical');
  
  if (critical) {
    DOM.weaknessBanner.classList.remove('d-none');
    const textbook = state.textbookMapping[critical.topic];
    DOM.weaknessBannerText.textContent = `Weakness detected in "${critical.topic}" (${critical.accuracy}% accuracy). Review the ${textbook ? textbook.book : 'school textbooks'}.`;
  } else {
    DOM.weaknessBanner.classList.add('d-none');
  }
}

// Get average scores of tested topics
function getTopicWeaknessReport() {
  const history = state.testHistory;
  if (history.length === 0) return [];
  
  // Group results by topic
  const topicStats = {};
  history.forEach(session => {
    if (!topicStats[session.topic]) {
      topicStats[session.topic] = { correct: 0, total: 0 };
    }
    topicStats[session.topic].correct += session.correctCount;
    topicStats[session.topic].total += session.totalCount;
  });
  
  return Object.keys(topicStats).map(topicName => {
    const stats = topicStats[topicName];
    const pct = Math.round((stats.correct / stats.total) * 100);
    
    let status = 'good';
    if (pct < 70) {
      status = 'critical';
    } else if (pct < 85) {
      status = 'warning';
    }
    
    return {
      topic: topicName,
      accuracy: pct,
      status: status
    };
  });
}

// Filter questions by active Group, type (pyq vs practice), and batch
function getFilteredQuestions(subject = "Economy", topic = null, type = null, batch = null) {
  return state.questions.filter(q => {
    // Subject filter
    const matchesSubject = q.subject.toLowerCase() === subject.toLowerCase();
    
    // Topic filter
    const matchesTopic = topic ? q.topic === topic : true;
    
    // Type filter
    const matchesType = type ? q.type === type : true;
    
    // Batch filter
    const matchesBatch = batch ? q.batch === batch : true;
    
    // Group exam filter: 
    // TNPSC Syllabus details overlaps, so we display:
    // 1. Group-specific exams (e.g. Group 4 matches G4)
    // 2. "Other Exams" (Gazetted/Technical exam crops) to guarantee sufficient question volume for the POC
    // 3. Practice questions are generated from textbooks and apply to all groups
    let matchesGroup = false;
    if (q.type === 'practice') {
      matchesGroup = true;
    } else {
      if (state.activeGroup === 'Group 1') {
        matchesGroup = q.group === 'Group 1' || q.group === 'Other Exams';
      } else if (state.activeGroup === 'Group 2') {
        matchesGroup = q.group === 'Group 2' || q.group === 'Other Exams';
      } else if (state.activeGroup === 'Group 4') {
        matchesGroup = q.group === 'Group 4' || q.group === 'Other Exams';
      }
    }
    
    return matchesSubject && matchesTopic && matchesGroup && matchesType && matchesBatch;
  });
}

// ==========================================================================
// SYLLABUS & TOPICS VIEW
// ==========================================================================
function renderSyllabusTopics() {
  DOM.topicsContainer.innerHTML = '';
  
  // Update header text based on active subject
  const syllabusHeader = document.querySelector('#screen-syllabus h2');
  if (syllabusHeader) {
    if (state.activeSubject === 'Economy') {
      syllabusHeader.textContent = 'Indian Economy';
    } else if (state.activeSubject === 'Polity') {
      syllabusHeader.textContent = 'Indian Polity';
    } else {
      syllabusHeader.textContent = 'Current Affairs';
    }
  }
  
  // Discover distinct topics in questions for the active subject
  const topics = Array.from(new Set(state.questions
    .filter(q => q.subject.toLowerCase() === state.activeSubject.toLowerCase())
    .map(q => q.topic)
  ));
  
  topics.forEach(topicName => {
    const filteredQs = getFilteredQuestions(state.activeSubject, topicName);
    if (filteredQs.length === 0) return; // Skip if no questions match this group
    
    // Get past records for this topic
    const topicTests = state.testHistory.filter(h => h.topic === topicName && h.group === state.activeGroup);
    
    let badgeText = 'Not Started';
    let badgeClass = 'blue';
    
    if (topicTests.length > 0) {
      let totalCorrect = 0;
      let totalSolved = 0;
      topicTests.forEach(t => {
        totalCorrect += t.correctCount;
        totalSolved += t.totalCount;
      });
      const accuracy = Math.round((totalCorrect / totalSolved) * 100);
      
      badgeText = `${accuracy}% Correct`;
      if (accuracy < 70) {
        badgeClass = 'red';
      } else if (accuracy < 85) {
        badgeClass = 'blue';
      } else {
        badgeClass = 'green';
      }
    }
    
    const card = document.createElement('div');
    card.className = 'topic-card';
    card.innerHTML = `
      <div class="topic-info-side">
        <h4>${topicName}</h4>
        <div class="topic-stats-row">
          <span class="topic-badge ${badgeClass}">${badgeText}</span>
          <span class="topic-q-count">${filteredQs.length} Questions</span>
        </div>
      </div>
      <button class="topic-start-btn" data-topic="${topicName}">▶</button>
    `;
    
    DOM.topicsContainer.appendChild(card);
  });
  
  // Attach start button event listeners
  DOM.topicsContainer.querySelectorAll('.topic-start-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const topic = e.target.getAttribute('data-topic');
      state.activeTopic = topic;
      navigateTo('screen-topic-detail');
    });
  });
}

// Render Topic Detail Screen
function renderTopicDetailScreen() {
  const topic = state.activeTopic;
  if (!topic) return;
  
  DOM.topicDetailTitle.textContent = topic;
  
  // 1. Get PYQ count
  const pyqs = getFilteredQuestions(state.activeSubject, topic, "pyq");
  const pyqCard = document.getElementById('topic-detail-pyq-card');
  const pyqHeader = pyqCard ? pyqCard.previousElementSibling : null;
  
  if (pyqs.length === 0) {
    if (pyqCard) pyqCard.style.display = 'none';
    if (pyqHeader && pyqHeader.classList.contains('section-title-row')) pyqHeader.style.display = 'none';
  } else {
    if (pyqCard) pyqCard.style.display = 'block';
    if (pyqHeader && pyqHeader.classList.contains('section-title-row')) pyqHeader.style.display = 'flex';
    DOM.topicDetailPyqCount.textContent = `${pyqs.length} PYQs Available`;
    DOM.btnStartPyq.disabled = false;
  }
  
  // 2. Render Practice Batches
  DOM.topicDetailBatchesContainer.innerHTML = '';
  
  // Get all unique practice batches in state.questions for this topic
  const batches = Array.from(new Set(
    state.questions
      .filter(q => q.topic === topic && q.type === 'practice')
      .map(q => q.batch)
  )).filter(Boolean);
  
  if (batches.length === 0) {
    DOM.topicDetailBatchesContainer.innerHTML = `<p class="text-muted" style="font-size: 13px; text-align: center; margin-top: 10px;">No practice batches generated yet for this topic.</p>`;
    return;
  }
  
  batches.sort().forEach(batchName => {
    const batchQs = getFilteredQuestions(state.activeSubject, topic, "practice", batchName);
    
    // Check if this batch has been completed
    const batchTests = state.testHistory.filter(h => h.topic === topic && h.group === 'Practice' && h.questions[0] && h.questions[0].batch === batchName);
    
    let badgeText = 'Not Started';
    let badgeClass = 'blue';
    
    if (batchTests.length > 0) {
      let totalCorrect = 0;
      let totalSolved = 0;
      batchTests.forEach(t => {
        totalCorrect += t.correctCount;
        totalSolved += t.totalCount;
      });
      const accuracy = Math.round((totalCorrect / totalSolved) * 100);
      badgeText = `${accuracy}% Score`;
      badgeClass = accuracy < 70 ? 'red' : (accuracy < 85 ? 'blue' : 'green');
    }
    
    const batchCard = document.createElement('div');
    batchCard.className = 'topic-card';
    batchCard.style.padding = '12px 16px';
    batchCard.innerHTML = `
      <div class="topic-info-side">
        <h4 style="font-family: var(--font-header); font-size: 14px; font-weight: 600;">${batchName}</h4>
        <div class="topic-stats-row">
          <span class="topic-badge ${badgeClass}">${badgeText}</span>
          <span class="topic-q-count">${batchQs.length} Questions</span>
        </div>
      </div>
      <button class="topic-start-btn batch-start-btn" data-batch="${batchName}" style="background: var(--accent-gradient); box-shadow: var(--shadow-glow); border: none; padding: 6px 12px; border-radius: var(--radius-sm); color: #fff; font-size: 12px; font-weight: 700; width: auto; height: auto;">Start</button>
    `;
    
    batchCard.querySelector('.batch-start-btn').addEventListener('click', () => {
      startQuiz(topic, "practice", batchName);
    });
    
    DOM.topicDetailBatchesContainer.appendChild(batchCard);
  });
}

// ==========================================================================
// QUIZ ENGINE
// ==========================================================================
function startQuiz(topic, type = null, batch = null) {
  // Get matching questions
  const availableQs = getFilteredQuestions(state.activeSubject, topic, type, batch);
  if (availableQs.length === 0) {
    alert("No questions available for this topic and parameters.");
    return;
  }
  
  // For practice batches, take all available questions. For PYQs, take up to 10.
  const countToPick = type === 'practice' ? availableQs.length : Math.min(10, availableQs.length);
  
  const shuffled = [...availableQs].sort(() => 0.5 - Math.random());
  const selectedQs = shuffled.slice(0, countToPick);
  
  // Initialize quiz state
  state.currentTest = {
    topic: topic,
    type: type,
    batch: batch,
    questions: selectedQs,
    currentIndex: 0,
    answers: {},
    startTime: Date.now(),
    timeLeft: selectedQs.length * 60, // 60s per question
    timer: null
  };
  
  // Update UI Elements
  DOM.quizTopicDisplay.textContent = type === 'practice' ? `${topic} (${batch})` : `${topic} (PYQs)`;
  updateQuizQuestion();
  navigateTo('screen-quiz');
  
  // Start Timer
  startQuizTimer();
}

function startQuizTimer() {
  if (state.currentTest.timer) clearInterval(state.currentTest.timer);
  
  const updateTimerDisplay = () => {
    const test = state.currentTest;
    const mins = Math.floor(test.timeLeft / 60);
    const secs = test.timeLeft % 60;
    DOM.quizTimerDisplay.textContent = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    
    if (test.timeLeft <= 0) {
      clearInterval(test.timer);
      alert("Time is up! Submitting your answers.");
      submitQuiz();
    }
    test.timeLeft--;
  };
  
  updateTimerDisplay();
  state.currentTest.timer = setInterval(updateTimerDisplay, 1000);
}

function updateQuizQuestion() {
  const test = state.currentTest;
  const index = test.currentIndex;
  const question = test.questions[index];
  
  // Update progress
  DOM.quizProgressText.textContent = `Question ${index + 1} of ${test.questions.length}`;
  const pct = Math.round(((index + 1) / test.questions.length) * 100);
  DOM.quizProgressBarFill.style.width = `${pct}%`;
  
  // Question text
  DOM.quizQuestionEn.innerHTML = question.question_en.replace(/\n/g, '<br>');
  DOM.quizQuestionTa.innerHTML = question.question_ta ? question.question_ta.replace(/\n/g, '<br>') : "தமிழ் வினா விடுபட்டுள்ளது.";
  
  // Options
  DOM.quizOptionsContainer.innerHTML = '';
  question.options.forEach(opt => {
    // If Tamil option is missing or null, provide fallbacks (specifically for Answer Not Known options)
    let optTextTa = opt.text_ta;
    if (opt.key === 'E' && !optTextTa) {
      optTextTa = "விடை தெரியவில்லை"; // standard TNPSC E option
    }
    if (optTextTa === opt.text_en) {
      optTextTa = "";
    }
    
    const optionDiv = document.createElement('div');
    optionDiv.className = `option-item ${test.answers[index] === opt.key ? 'selected' : ''}`;
    optionDiv.setAttribute('data-key', opt.key);
    optionDiv.innerHTML = `
      <div class="option-key">${opt.key}</div>
      <div class="option-text-wrapper">
        <div class="option-text-en">${opt.text_en}</div>
        ${optTextTa ? `<div class="option-text-ta">${optTextTa}</div>` : ''}
      </div>
    `;
    
    optionDiv.addEventListener('click', () => selectOption(opt.key));
    DOM.quizOptionsContainer.appendChild(optionDiv);
  });
  
  // Nav buttons states
  DOM.quizPrevBtn.disabled = index === 0;
  
  if (index === test.questions.length - 1) {
    DOM.quizNextBtn.textContent = 'Submit';
    DOM.quizNextBtn.classList.add('submit-type');
  } else {
    DOM.quizNextBtn.textContent = 'Next';
    DOM.quizNextBtn.classList.remove('submit-type');
  }
}

function selectOption(key) {
  const test = state.currentTest;
  test.answers[test.currentIndex] = key;
  
  // Redraw option selection highlight
  const optionItems = DOM.quizOptionsContainer.querySelectorAll('.option-item');
  optionItems.forEach(item => {
    if (item.getAttribute('data-key') === key) {
      item.classList.add('selected');
    } else {
      item.classList.remove('selected');
    }
  });
}

function navigateQuizQuestion(direction) {
  const test = state.currentTest;
  
  // If next click on last question -> trigger Submit
  if (direction === 1 && test.currentIndex === test.questions.length - 1) {
    submitQuiz();
    return;
  }
  
  test.currentIndex += direction;
  updateQuizQuestion();
}

function quitQuiz() {
  if (confirm("Are you sure you want to quit this test? Your progress will be lost.")) {
    const test = state.currentTest;
    clearInterval(test.timer);
    state.currentTest = null;
    if (state.activeTopic) {
      navigateTo('screen-topic-detail');
    } else {
      navigateTo('screen-syllabus');
    }
  }
}

function submitQuiz() {
  const test = state.currentTest;
  clearInterval(test.timer);
  
  // Calc score details
  let correctCount = 0;
  test.questions.forEach((q, idx) => {
    if (test.answers[idx] === q.correct_option) {
      correctCount++;
    }
  });
  
  const totalCount = test.questions.length;
  const timeTaken = Math.round((Date.now() - test.startTime) / 1000);
  
  // Session object
  const session = {
    id: 'test_' + Date.now(),
    topic: test.topic,
    group: test.type === 'practice' ? 'Practice' : state.activeGroup,
    questions: test.questions,
    answers: test.answers,
    correctCount: correctCount,
    totalCount: totalCount,
    timeTaken: timeTaken,
    timestamp: new Date().toLocaleDateString()
  };
  
  // Save to state history
  state.testHistory.unshift(session); // Add to beginning
  localStorage.setItem('tnpsc_test_history', JSON.stringify(state.testHistory));
  
  // Clear quiz state
  state.currentTest = null;
  
  // Render results view
  displayResults(session);
}

// ==========================================================================
// RESULTS VIEW & RENDERERS
// ==========================================================================
function displayResults(session) {
  DOM.resultsTopicDisplay.textContent = session.topic;
  DOM.resultsScoreValue.textContent = `${session.correctCount}/${session.totalCount}`;
  
  const accuracy = Math.round((session.correctCount / session.totalCount) * 100);
  DOM.resultsAccuracyPct.textContent = `${accuracy}% Accuracy`;
  
  // Animate Circular Progress score ring
  // Stroke Dasharray total length = 263.8
  const offset = 263.8 * (1 - (session.correctCount / session.totalCount));
  DOM.resultsDasharray.style.strokeDashoffset = offset;
  
  // Feedbacks
  let feedback = "Review your textbook references below to improve.";
  if (accuracy === 100) feedback = "Outstanding! Perfect score. You've mastered this topic!";
  else if (accuracy >= 80) feedback = "Excellent job! You have solid command over this area.";
  else if (accuracy >= 60) feedback = "Good effort, but review the recommended pages to boost score.";
  DOM.resultsFeedbackMessage.textContent = feedback;
  
  DOM.resultsCorrectCount.textContent = session.correctCount;
  DOM.resultsWrongCount.textContent = session.totalCount - session.correctCount;
  
  // Format duration
  const mins = Math.floor(session.timeTaken / 60);
  const secs = session.timeTaken % 60;
  DOM.resultsTimeTaken.textContent = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
  
  // Review answers list
  DOM.resultsReviewContainer.innerHTML = '';
  session.questions.forEach((q, idx) => {
    const userSelected = session.answers[idx];
    const isCorrect = userSelected === q.correct_option;
    
    const card = document.createElement('div');
    card.className = `review-card ${isCorrect ? 'correct' : 'wrong'}`;
    
    // Header
    card.innerHTML = `
      <div class="review-question-text">
        <strong>Q${idx+1}.</strong> ${q.question_en}<br>
        <span class="text-muted" style="font-size:12px;">${q.question_ta || ''}</span>
      </div>
      <div class="review-choices"></div>
    `;
    
    const choicesList = card.querySelector('.review-choices');
    q.options.forEach(opt => {
      let optTextTa = opt.text_ta;
      if (opt.key === 'E' && !optTextTa) optTextTa = "விடை தெரியவில்லை";
      if (optTextTa === opt.text_en) optTextTa = "";
      
      const isThisCorrect = opt.key === q.correct_option;
      const isThisUserSelection = opt.key === userSelected;
      
      let modifierClass = '';
      let badgeHtml = '';
      
      if (isThisCorrect) {
        modifierClass = 'correct';
        badgeHtml = `<span class="review-choice-badge correct">Correct</span>`;
      } else if (isThisUserSelection && !isCorrect) {
        modifierClass = 'user-wrong';
        badgeHtml = `<span class="review-choice-badge wrong">Your Pick</span>`;
      }
      
      const choiceDiv = document.createElement('div');
      choiceDiv.className = `review-choice-item ${modifierClass}`;
      choiceDiv.innerHTML = `
        <span class="review-choice-key">${opt.key}.</span>
        <div style="display:flex; flex-direction:column;">
          <span>${opt.text_en}</span>
          ${optTextTa ? `<span class="text-muted" style="font-size:11px;">${optTextTa}</span>` : ''}
        </div>
        ${badgeHtml}
      `;
      choicesList.appendChild(choiceDiv);
    });
    
    // Add Textbook reference matching the question's topic
    const textbook = state.textbookMapping[q.topic];
    if (textbook) {
      const expDiv = document.createElement('div');
      expDiv.className = 'review-explanation';
      expDiv.innerHTML = `
        📖 <strong>Study Guide Reference:</strong><br>
        ${textbook.book} &bull; ${textbook.chapter}<br>
        <span style="color:var(--primary-glow); font-weight:600;">Recommended Reading: ${textbook.pages}</span>
      `;
      card.appendChild(expDiv);
    }
    
    DOM.resultsReviewContainer.appendChild(card);
  });
  
  navigateTo('screen-results');
}

// ==========================================================================
// AI STUDY ADVISOR & RECOMMENDATION SYSTEM
// ==========================================================================
function updateAdvisorScreen() {
  DOM.advisorRecommendationsList.innerHTML = '';
  
  const report = getTopicWeaknessReport();
  
  if (state.testHistory.length === 0) {
    DOM.advisorSummaryText.textContent = "Take topic-wise quizzes in the 'Syllabus' tab. The Advisor will analyze your scores and build a tailored study guide highlighting weak spots.";
    DOM.weaknessReviewCta.classList.add('d-none');
    
    // Render blank or initial study topics list as placeholder
    Object.keys(state.textbookMapping).forEach(topicKey => {
      renderAdvisorCard({ topic: topicKey, accuracy: null, status: 'none' });
    });
    return;
  }
  
  // Set overview message
  const criticalList = report.filter(r => r.status === 'critical');
  const warningList = report.filter(r => r.status === 'warning');
  
  if (criticalList.length > 0) {
    DOM.advisorSummaryText.textContent = `Alert: We detected weaknesses in ${criticalList.length} topic(s). Follow the textbook guides below to improve.`;
  } else if (warningList.length > 0) {
    DOM.advisorSummaryText.textContent = `You're doing well! Just a few areas in Economics require fine-tuning.`;
  } else {
    DOM.advisorSummaryText.textContent = `Outstanding work! You've achieved mastery (85%+ accuracy) across all tested Economics topics!`;
  }
  
  // Weakness Review CTA logic
  // Gather incorrect questions from test history
  const incorrectQuestions = getIncorrectQuestions();
  if (incorrectQuestions.length > 0) {
    DOM.weaknessReviewCta.classList.remove('d-none');
    DOM.weaknessReviewDescription.textContent = `You have ${incorrectQuestions.length} questions previously answered incorrectly. Boost mastery by repeating them!`;
    DOM.advisorLaunchReviewBtn.textContent = `Start Review (${incorrectQuestions.length} Qs)`;
  } else {
    DOM.weaknessReviewCta.classList.add('d-none');
  }
  
  // Render recommendations matching syllabus topics
  const topicsInApp = Array.from(new Set(state.questions.map(q => q.topic)));
  
  topicsInApp.forEach(topicName => {
    const stats = report.find(r => r.topic === topicName);
    if (stats) {
      renderAdvisorCard(stats);
    } else {
      renderAdvisorCard({ topic: topicName, accuracy: null, status: 'none' });
    }
  });
}

function renderAdvisorCard(stats) {
  const textbook = state.textbookMapping[stats.topic];
  if (!textbook) return; // Skip if no mapping exists for this topic
  
  const card = document.createElement('div');
  
  let borderClass = 'good';
  let badgeText = 'Mastery achieved';
  let badgeClass = 'good';
  let advice = "Your accuracy is high. Keep practicing and revise before exams.";
  
  if (stats.status === 'critical') {
    borderClass = 'critical';
    badgeText = `${stats.accuracy}% Accuracy`;
    badgeClass = 'critical';
    advice = `<strong>Critical Action Required:</strong> Your score is low. Allocate study time to read the following textbook pages. Pay close attention to: ${textbook.focus}`;
  } else if (stats.status === 'warning') {
    borderClass = 'warning';
    badgeText = `${stats.accuracy}% Accuracy`;
    badgeClass = 'warning';
    advice = `<strong>Focus Required:</strong> You are very close to mastery. Review these textbook concepts to eliminate simple mistakes: ${textbook.focus}`;
  } else if (stats.status === 'none') {
    borderClass = 'none';
    badgeText = 'Not Tested';
    badgeClass = 'warning';
    advice = "No score data yet. Complete a quiz to analyze your performance.";
  }
  
  card.className = `advisor-card ${borderClass}`;
  card.innerHTML = `
    <div class="advisor-card-header">
      <span class="advisor-card-title">${textbook.titleTa}<br><small style="color:var(--text-muted);">${stats.topic}</small></span>
      <span class="advisor-card-badge ${badgeClass}">${badgeText}</span>
    </div>
    <div class="advisor-card-body">
      <p>${advice}</p>
    </div>
    ${stats.status !== 'none' ? `
      <div class="advisor-card-recommendation">
        <span class="book-icon">📚</span>
        <div class="book-details">
          <span class="book-title">${textbook.book}</span>
          <span class="book-chapters">${textbook.chapter}</span>
          <span style="color:var(--primary-glow); font-weight:700; font-size:11px; margin-top:2px;">Recommended study: ${textbook.pages}</span>
        </div>
      </div>
    ` : ''}
    <button class="advisor-card-action-btn" data-topic="${stats.topic}">Practice This Topic</button>
  `;
  
  card.querySelector('.advisor-card-action-btn').addEventListener('click', () => {
    startQuiz(stats.topic);
  });
  
  DOM.advisorRecommendationsList.appendChild(card);
}

// Gather unique questions got wrong in past history
function getIncorrectQuestions() {
  const incorrectMap = new Map();
  const correctSet = new Set();
  
  // Go through history chronological (oldest to newest) to see what is currently incorrect
  // Reverse history list for chronological sweep
  const chronoHistory = [...state.testHistory].reverse();
  
  chronoHistory.forEach(session => {
    Object.keys(session.answers).forEach(qIndexStr => {
      const qIndex = parseInt(qIndexStr);
      const question = session.questions[qIndex];
      const selected = session.answers[qIndex];
      
      if (question) {
        const qKey = question.question_en;
        if (selected === question.correct_option) {
          correctSet.add(qKey);
          incorrectMap.delete(qKey); // If got correct later, remove from wrong list
        } else {
          if (!correctSet.has(qKey)) {
            incorrectMap.set(qKey, question); // Add to wrong list
          }
        }
      }
    });
  });
  
  return Array.from(incorrectMap.values());
}

function startWeaknessReviewQuiz() {
  const incorrectQs = getIncorrectQuestions();
  if (incorrectQs.length === 0) return;
  
  // Shuffle and take top 10
  const shuffled = incorrectQs.sort(() => 0.5 - Math.random());
  const selectedQs = shuffled.slice(0, Math.min(10, shuffled.length));
  
  state.currentTest = {
    topic: "Weakness Review",
    questions: selectedQs,
    currentIndex: 0,
    answers: {},
    startTime: Date.now(),
    timeLeft: selectedQs.length * 60,
    timer: null
  };
  
  DOM.quizTopicDisplay.textContent = "Weakness Review";
  updateQuizQuestion();
  navigateTo('screen-quiz');
  
  startQuizTimer();
}

// Fallback Mock Questions to run offline if network fails to fetch JSON
function getFallbackQuestions() {
  return [
    {
      "question_en": "Mixed Economy implies",
      "question_ta": "கலப்பு பொருளாதாரம் --------------- குறிக்கிறது.",
      "options": [
        { "key": "A", "text_en": "Co-existence of Small and Large industries", "text_ta": "சிறு மற்றும் பேரளவுத் தொழில்கள் இணைந்து செயல்படுதல்" },
        { "key": "B", "text_en": "Co-existence of Public and Private sectors", "text_ta": "பொது மற்றும் தனியார் துறைகள் இணைந்து செயல்படுதல்" },
        { "key": "C", "text_en": "Co-existence of Labour intensive and Capital intensive technology", "text_ta": "உழைப்பு தொழில்நுட்ப செறிவு மற்றும் மூலதன தொழில்நுட்ப செறிவு இணைந்து செயல்படுதல்" },
        { "key": "D", "text_en": "Co-existence of National and Foreign companies", "text_ta": "தேசிய மற்றும் அயல்நாட்டு நிறுவனங்கள் இணைந்து செயல்படுதல்" }
      ],
      "correct_option": "B",
      "subject": "Economy",
      "topic": "Nature of Indian Economy",
      "source_exam": "Mock Exam",
      "group": "Other Exams"
    }
  ];
}
