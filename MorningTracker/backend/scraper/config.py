"""
Configuration for the NEXUS Scraper Engine.
Centralized keywords, regions, and search modifiers.
"""

SECTOR_KEYWORDS = {
    "ai": [
        "artificial intelligence", "AI", "generative AI", "GenAI", "machine learning", "deep learning", "large language models", "LLM", "GPT", "AI models", "AI systems", "AI tools", "AI platform", "AI startup", "AI research", "AI development", "AI innovation", "AI adoption", "AI deployment", "AI applications", "AI solutions", "AI infrastructure", "AI chips", "AI semiconductor", "AI hardware", "AI regulation", "AI policy", "responsible AI", "ethical AI", "explainable AI", "XAI", "AI governance", "natural language processing", "NLP", "computer vision", "speech recognition", "AI chatbot", "conversational AI", "AI assistant", "AI agents", "autonomous AI", "multimodal AI", "reinforcement learning", "neural networks", "training models", "AI datasets", "model training", "model inference", "AI cloud", "AI in India", "India AI mission", "AI startups India", "AI funding", "AI investment", "AI unicorn", "AI hiring", "AI jobs", "AI layoffs", "AI breakthroughs", "AI trends", "OpenAI", "ChatGPT", "GPT-4", "GPT-5", "Google DeepMind", "Google Gemini", "Gemini AI", "Microsoft AI", "Copilot", "GitHub Copilot", "NVIDIA", "Anthropic", "Claude", "Claude AI", "Meta AI", "LLaMA", "IBM Watson", "Stability AI", "Stable Diffusion", "Midjourney", "Hugging Face", "Cohere", "Inflection AI", "Character AI", "Perplexity AI", "Grok AI", "xAI", "Databricks", "Snowflake", "Palantir", "Adobe Firefly", "Amazon Bedrock", "Baidu AI", "Tencent AI", "Sam Altman", "Sundar Pichai", "Satya Nadella", "Jensen Huang", "Demis Hassabis", "Mark Zuckerberg"
    ],
    "tech": [
        "technology", "digital", "tech", "IT", "software", "internet", "data", "cloud", "cloud computing", "cloud services", "data center", "data centres", "AI", "artificial intelligence", "generative AI", "machine learning", "data analytics", "big data", "data science", "cybersecurity", "cyber security", "data privacy", "data protection", "data breach", "cyber attack", "hacking", "ransomware", "startup", "startups", "tech startup", "SaaS", "app", "mobile app", "super app", "platform", "digital platform", "automation", "robotics", "innovation", "emerging technology", "deep tech", "semiconductor", "semiconductors", "chips", "chip manufacturing", "telecom", "telecommunications", "5G", "6G", "network", "broadband", "IT services", "tech industry", "digital transformation", "API", "APIs", "developer", "developers", "coding", "programming", "web development", "fintech", "healthtech", "edtech", "agritech", "proptech", "insurtech", "gaming", "blockchain", "web3", "crypto", "IoT", "internet of things", "electric vehicles", "EV", "EV tech", "battery technology", "enterprise tech", "cloud migration", "cloud infrastructure", "cyber security breach", "zero trust security", "AI regulation", "tech policy", "digital India", "DPI (digital public infrastructure)", "UPI", "Aadhaar", "ONDC", "startup funding", "funding", "venture capital", "VC funding", "unicorn", "unicorn startup", "IPO", "tech IPO", "layoffs", "tech layoffs", "hiring", "tech hiring", "TCS", "Infosys", "Wipro", "HCLTech", "Tech Mahindra", "Microsoft", "Google", "Apple", "Amazon", "Meta", "IBM", "Oracle", "Cisco", "Intel", "AMD", "SAP", "Salesforce", "ServiceNow", "Dell Technologies", "HP", "Reliance Jio", "Airtel", "Vodafone Idea", "Jio Platforms", "Qualcomm", "Ericsson", "Nokia", "Natarajan Chandrasekaran", "Thierry Delaporte", "C Vijayakumar", "Arvind Krishna"
    ],
    "foods and drinks": [
        "food industry", "food sector", "food business", "food services", "food processing", "processed food", "packaged food", "FMCG food", "dairy industry", "dairy products", "milk production", "beverage industry", "beverages", "soft drinks", "carbonated drinks", "alcoholic beverages", "non-alcoholic beverages", "bottled water", "energy drinks", "tea industry", "coffee industry", "quick commerce", "food delivery", "online food delivery", "restaurant industry", "restaurants", "QSR", "quick service restaurants", "cloud kitchen", "dark kitchen", "food tech", "food startup", "food chain", "fast food", "casual dining", "fine dining", "menu pricing", "food prices", "inflation food prices", "supply chain food", "cold storage", "food logistics", "agriculture supply chain", "agri supply", "food exports", "food imports", "FSSAI", "food safety", "food regulation", "food standards", "packaged snacks", "ready to eat food", "ready to cook", "frozen food", "organic food", "plant based food", "protein foods", "nutrition products", "health drinks", "bottled beverages", "brewery", "distillery", "Nestle India", "ITC", "Hindustan Unilever", "Britannia", "Amul", "Mother Dairy", "PepsiCo India", "Coca-Cola India", "Starbucks India", "Domino’s India", "Jubilant FoodWorks", "Parle Agro", "Dabur", "Marico", "Varun Beverages", "Zomato", "Swiggy", "Zepto Cafe", "Blinkit"
    ],
    "healthcare": [
        "healthcare", "healthcare sector", "healthcare services", "hospitals", "hospital chain", "hospital network", "clinical services", "medical services", "patient care", "diagnostics", "diagnostic labs", "pathology labs", "radiology", "imaging", "telemedicine", "telehealth", "digital health", "healthtech", "e-health", "electronic health records", "EHR", "EMR", "medical devices", "medical equipment", "pharmaceuticals", "pharma", "drug development", "drug approval", "clinical trials", "vaccine", "vaccination", "immunization", "public health", "healthcare policy", "health ministry", "Ayushman Bharat", "National Health Mission", "health insurance", "medical insurance", "insurance claims", "disease outbreak", "epidemic", "pandemic", "infectious diseases", "chronic diseases", "cancer treatment", "oncology", "cardiology", "diabetes", "mental health", "maternal health", "child health", "primary healthcare", "healthcare infrastructure", "ICU", "ventilators", "medical research", "biotech", "biotechnology", "genomics", "precision medicine", "wearable health tech", "health monitoring", "AI in healthcare", "medical AI", "hospital management systems", "Apollo Hospitals", "Fortis Healthcare", "Max Healthcare", "Narayana Health", "Aster DM Healthcare", "Dr. Reddy’s Laboratories", "Sun Pharma", "Cipla", "Lupin", "Biocon", "Serum Institute of India", "Bharat Biotech", "Zydus Lifesciences", "Pfizer India", "GSK India", "Practo", "PharmEasy", "Tata 1mg", "Medanta", "Kiran Mazumdar-Shaw", "Devi Shetty"
    ],
    "travel": [
        "travel", "tourism", "tourism industry", "hospitality", "hotels", "resorts", "airlines", "aviation", "airports", "flight bookings", "airline routes", "international travel", "domestic travel", "business travel", "leisure travel", "travel technology", "travel startup", "online travel agency", "OTA", "holiday packages", "tourism policy", "visa", "visa policy", "passport services", "pilgrimage tourism", "eco tourism", "adventure tourism", "luxury travel", "travel trends", "tourism growth", "hotel occupancy", "hospitality sector", "MakeMyTrip", "EaseMyTrip", "Yatra", "Airbnb", "OYO", "Indigo", "Air India", "Akasa Air", "SpiceJet", "Vistara", "IRCTC", "Thomas Cook India", "Cox & Kings"
    ],
    "consultancies": [
        "consulting firms", "consultancy firms", "consulting industry", "consulting services", "advisory services", "business consulting", "management consulting", "strategy consulting", "IT consulting", "technology consulting", "digital consulting", "financial consulting", "risk consulting", "tax consulting", "audit firms", "professional services firms", "Big Four", "consulting companies", "advisory firms", "consulting contracts", "consulting deals", "client mandates", "consulting projects", "digital transformation consulting", "ERP consulting", "SAP consulting", "cloud consulting", "cybersecurity consulting", "AI consulting", "data consulting", "analytics consulting", "outsourcing services", "business process outsourcing", "BPO", "knowledge process outsourcing", "KPO", "shared services", "global capability centres", "GCC", "consulting hiring", "consulting jobs", "lateral hiring consulting", "consulting layoffs", "consulting expansion", "consulting acquisitions", "consulting mergers", "consulting partnerships", "consulting revenue", "consulting growth", "consulting market India", "consulting reports", "consulting insights", "Accenture", "Deloitte", "PwC", "EY", "KPMG", "McKinsey", "BCG", "Bain & Company", "Infosys Consulting", "TCS Consulting", "Capgemini", "Cognizant", "WNS Global", "Genpact", "Fractal Analytics", "ZS Associates", "Alvarez & Marsal", "Protiviti"
    ],
    "startups": [
        "startup", "startups", "startup ecosystem", "startup India", "startup funding", "seed funding", "pre-seed funding", "Series A", "Series B", "Series C", "growth stage funding", "venture capital", "VC funding", "angel investors", "angel funding", "private equity", "PE funding", "funding round", "investment", "investor", "strategic investment", "startup valuation", "valuation", "unicorn", "unicorn startup", "decacorn", "IPO", "startup IPO", "listing", "acquisition", "merger", "startup acquisition", "exit", "founder", "co-founder", "entrepreneurship", "entrepreneur", "incubator", "accelerator", "startup accelerator", "startup incubator", "venture studio", "bootstrapped startup", "early-stage startup", "growth-stage startup", "startup hiring", "startup layoffs", "startup expansion", "startup ecosystem India", "D2C startup", "direct-to-consumer", "SaaS startup", "fintech startup", "healthtech startup", "edtech startup", "agritech startup", "proptech startup", "insurtech startup"
    ],
    "lifestyle": [
        "lifestyle industry", "fashion industry", "apparel industry", "clothing industry", "fashion brands", "apparel brands", "clothing brands", "luxury fashion", "premium fashion", "fast fashion", "ethnic wear", "western wear", "designer wear", "fashion retail", "apparel retail", "fashion e-commerce", "beauty industry", "cosmetics industry", "skincare", "skincare products", "makeup", "beauty products", "personal care", "personal care products", "grooming", "grooming products", "haircare", "haircare products", "fragrance", "perfumes", "luxury beauty", "premium beauty", "D2C brands", "direct to consumer brands", "fashion startup", "beauty startup", "influencer marketing", "celebrity brands", "brand endorsements", "fashion shows", "fashion week", "runway shows", "designer collections", "new collection launch", "product launch", "brand launch", "retail expansion", "store expansion", "flagship store", "omnichannel retail", "e-commerce fashion", "online beauty retail"
    ],
    "policies": [
        "government policy", "government policies", "public policy", "policy decision", "policy changes", "central government", "state government", "union government", "ministry", "government scheme", "government schemes", "flagship schemes", "welfare schemes", "budget", "union budget", "fiscal policy", "economic policy", "taxation policy", "tax policy", "GST", "GST council", "direct tax", "indirect tax", "income tax", "corporate tax", "subsidy", "subsidies", "regulatory framework", "regulation", "regulatory policy", "compliance", "policy reforms", "economic reforms", "parliament", "ordinance", "law", "legislation", "policy implementation", "RBI policy", "monetary policy", "repo rate", "NITI Aayog", "Digital India", "Make in India", "Startup India", "Skill India", "PLI scheme", "National Health Mission", "Ayushman Bharat", "education policy", "NEP", "healthcare policy", "energy policy", "renewable energy policy", "environmental policy"
    ],
    "stock market": [
        "stock market", "share market", "equity market", "stock exchange", "NSE", "BSE", "Sensex", "Nifty", "Nifty 50", "stock indices", "market indices", "stock trading", "trading session", "intraday trading", "bull market", "bear market", "stock rally", "market crash", "stock surge", "stock decline", "stock performance", "share price", "stock price", "market volatility", "FII", "DII", "mutual funds", "SIP", "hedge funds", "portfolio", "asset management", "wealth management", "dividends", "earnings", "quarterly results", "financial results", "profit", "revenue", "EBITDA", "brokerage", "analyst ratings", "derivatives", "futures", "options", "F&O", "commodity market", "gold prices", "crude oil prices", "forex", "currency market", "inflation", "interest rates", "RBI", "banking stocks", "financial sector"
    ],
    "real estate": [
        "real estate", "real estate sector", "property market", "housing market", "residential real estate", "commercial real estate", "office space", "retail space", "property development", "real estate development", "real estate projects", "housing projects", "property prices", "property rates", "housing prices", "real estate demand", "property demand", "housing demand", "property sales", "housing sales", "property transactions", "land acquisition", "construction", "infrastructure development", "builders", "developers", "affordable housing", "luxury housing", "smart cities", "urban development", "township projects", "rental housing", "leasing", "co-working spaces", "REITs", "property investment", "home loans", "mortgage", "RERA", "real estate regulation", "housing policy", "stamp duty", "property tax", "DLF", "Godrej Properties", "Oberoi Realty", "Prestige Estates", "Brigade Group", "Lodha Group", "Sobha Ltd"
    ]
}

SEARCH_MODIFIERS = [
    "news", "latest", "update", "report", "analysis", "market", "policy", "regulation",
    "research", "innovation", "trending", "forecast", "announcement", "investment",
    "funding", "startup", "expert", "interview", "review", "growth", "challenge", "impact",
    "press release", "summit", "conference", "breakthrough", "scandal", "lawsuit",
    "acquisition", "merger", "partnership", "collaboration", "patent", "earnings",
    "exclusive", "leaked", "roadmap", "demo", "unveiled", "launched", "unveiling",
    "rumor", "speculation", "leak", "investigation", "case study", "white paper",
    "competitor", "market analysis", "regulatory filing", "insider", "perspective",
    "industry outlook", "quarterly results", "stock performance", "hiring", "layoffs",
    "expansion", "strategy shift", "disruption", "threat", "opportunity", "ranking",
    "top 10", "comparison", "feature", "profile", "investigative", "opinion",
]

REGION_MAP = {
    "global":    {"geo": "US", "cities": []},
    "india":     {"geo": "IN", "cities": ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Kolkata", "Pune", "Ahmedabad", "Surat", "Lucknow", "Indore", "Bhopal", "Patna", "Jaipur", "Chandigarh", "Kochi", "Gurgaon", "Noida"]},
    "usa":       {"geo": "US", "cities": ["New York", "San Francisco", "Washington", "Chicago", "Los Angeles", "Austin", "Seattle", "Boston", "Dallas", "Houston", "Miami", "Denver", "Atlanta", "Phoenix", "Philadelphia"]},
    "uk":        {"geo": "GB", "cities": ["London", "Manchester", "Birmingham", "Edinburgh", "Glasgow", "Liverpool", "Leeds", "Bristol"]},
    "canada":    {"geo": "CA", "cities": ["Toronto", "Vancouver", "Montreal", "Ottawa", "Calgary", "Edmonton", "Quebec City"]},
    "japan":     {"geo": "JP", "cities": ["Tokyo", "Osaka", "Kyoto", "Yokohama", "Nagoya", "Sapporo", "Fukuoka"]},
    "australia": {"geo": "AU", "cities": ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide", "Canberra", "Gold Coast"]},
    "europe":    {"geo": "EU", "cities": ["Berlin", "Paris", "Madrid", "Rome", "Amsterdam", "Brussels", "Vienna", "Zurich", "Stockholm", "Dublin"]},
}

INDIAN_LANGUAGES = [
    {"name": "Hindi", "code": "hi", "ceid": "IN:hi"},
    {"name": "Bengali", "code": "bn", "ceid": "IN:bn"},
    {"name": "Marathi", "code": "mr", "ceid": "IN:mr"},
    {"name": "Telugu", "code": "te", "ceid": "IN:te"},
    {"name": "Tamil", "code": "ta", "ceid": "IN:ta"},
    {"name": "Gujarati", "code": "gu-IN", "ceid": "IN:gu"},
    {"name": "Malayalam", "code": "ml", "ceid": "IN:ml"},
    {"name": "Punjabi", "code": "pa-IN", "ceid": "IN:pa"},
    {"name": "English (India)", "code": "en-IN", "ceid": "IN:en"}
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
]
