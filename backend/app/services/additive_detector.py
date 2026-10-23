from __future__ import annotations

import re
from typing import Any, Literal

ConcernLevel = Literal["low", "moderate", "high"]

# Curated knowledge base of food additives and ingredients.
# Each entry includes scientific consensus, functional purpose,
# regulatory status, and evidence citations.
CURATED_ADDITIVES: list[dict[str, Any]] = [
    # ---------------- HIGH CONCERN ----------------
    {
        "id": "potassium-bromate",
        "name": "Potassium Bromate",
        "e_number": "E924",
        "synonyms": [
            "potassium bromate",
            "e924",
            "e-924",
            "e 924",
            "bromated flour",
            "potassium salt of bromic acid",
        ],
        "purpose": "Flour bleaching and dough strengthening oxidizer",
        "concern_level": "high",
        "concern_summary": (
            "Classified as a possible human carcinogen (Group 2B) by IARC. "
            "Animal studies demonstrate renal and thyroid tumors. Banned in "
            "the EU, UK, Canada, India, and China; restricted by the US FDA."
        ),
        "evidence_source": "IARC Monographs Vol. 73; JECFA Toxicological Evaluation",
        "regulatory_status": "Banned in EU, UK, Canada, India; restricted in USA",
        "recommendation": (
            "Avoid regular consumption. Choose unbromated bakery products."
        ),
    },
    {
        "id": "titanium-dioxide",
        "name": "Titanium Dioxide",
        "e_number": "E171",
        "synonyms": [
            "titanium dioxide",
            "e171",
            "e-171",
            "e 171",
            "ins 171",
            "ins171",
            "ci 77891",
            "titanium white",
            "food grade titanium dioxide",
        ],
        "purpose": "Opacifying whitening agent and color brightener",
        "concern_level": "high",
        "concern_summary": (
            "In 2021, the European Food Safety Authority (EFSA) concluded that "
            "titanium dioxide nanoparticles can no longer be considered safe as "
            "a food additive due to genotoxicity concerns and cellular accumulation."
        ),
        "evidence_source": "EFSA Panel on Food Additives and Flavourings (2021)",
        "regulatory_status": "Banned in the European Union (2022); under FDA re-evaluation",
        "recommendation": (
            "Avoid where possible, especially in confections, frostings, and sauces."
        ),
    },
    {
        "id": "brominated-vegetable-oil",
        "name": "Brominated Vegetable Oil (BVO)",
        "e_number": None,
        "synonyms": [
            "brominated vegetable oil",
            "bvo",
            "brominated soybean oil",
        ],
        "purpose": "Emulsifier and density stabilizer in citrus-flavored beverages",
        "concern_level": "high",
        "concern_summary": (
            "Bioaccumulates in body tissues and animal studies showed myocardial "
            "and thyroid toxicity. The US FDA concluded in 2024 that dietary use "
            "is no longer safe."
        ),
        "evidence_source": "US FDA Final Rule on BVO (2024); EFSA Safety Assessments",
        "regulatory_status": "Banned in US (FDA authorization revoked 2024); banned in EU",
        "recommendation": (
            "Avoid beverages containing BVO. Modern formulations use alternative stabilizers."
        ),
    },
    {
        "id": "partially-hydrogenated-oil",
        "name": "Partially Hydrogenated Oil (Trans Fat)",
        "e_number": None,
        "synonyms": [
            "partially hydrogenated oil",
            "partially hydrogenated soybean oil",
            "partially hydrogenated cottonseed oil",
            "partially hydrogenated vegetable oil",
            "trans fat",
            "artificial trans fat",
            "partially hydrogenated",
        ],
        "purpose": "Solid fat providing texture stability and extended shelf life",
        "concern_level": "high",
        "concern_summary": (
            "Strongly linked to coronary heart disease, elevated LDL cholesterol, "
            "reduced HDL cholesterol, and systemic vascular inflammation."
        ),
        "evidence_source": "WHO REPLACE Initiative; US FDA GRAS Removal Determination",
        "regulatory_status": "Prohibited in food by US FDA; strict <2% legal limits across EU",
        "recommendation": (
            "Avoid entirely. Look for products using unhydrogenated vegetable oils."
        ),
    },
    {
        "id": "propylparaben",
        "name": "Propylparaben",
        "e_number": "E216",
        "synonyms": [
            "propylparaben",
            "propyl paraben",
            "propyl 4-hydroxybenzoate",
            "sodium propylparaben",
            "e216",
            "e-216",
            "e217",
            "e-217",
            "ins 216",
        ],
        "purpose": "Antimicrobial preservative in tortillas and confectionery",
        "concern_level": "high",
        "concern_summary": (
            "Demonstrated endocrine-disrupting activity in animal models, "
            "interfering with reproductive hormone regulation and fertility markers."
        ),
        "evidence_source": "EFSA Scientific Opinion on Parabens; Regulation (EC) 1333/2008",
        "regulatory_status": "Prohibited from food use in the EU; restricted in US",
        "recommendation": (
            "Limit exposure by choosing paraben-free bakery and tortilla items."
        ),
    },
    {
        "id": "potassium-iodate",
        "name": "Potassium Iodate",
        "e_number": "E917",
        "synonyms": [
            "potassium iodate",
            "e917",
            "e-917",
            "ins 917",
        ],
        "purpose": "Flour treatment agent and oxidizing dough improver",
        "concern_level": "high",
        "concern_summary": (
            "Excessive exposure poses risks to thyroid homeostasis and renal "
            "function. Generally excluded from bakery standards internationally."
        ),
        "evidence_source": "JECFA Food Additive Series; Codex Alimentarius Standard 152",
        "regulatory_status": "Banned as a bread flour improver in EU and Canada",
        "recommendation": (
            "Avoid baked goods listing potassium iodate as a conditioner."
        ),
    },

    # ---------------- MODERATE CONCERN ----------------
    {
        "id": "sodium-nitrite",
        "name": "Sodium Nitrite",
        "e_number": "E250",
        "synonyms": [
            "sodium nitrite",
            "e250",
            "e-250",
            "ins 250",
            "nitrite",
        ],
        "purpose": "Curing agent preventing botulism and maintaining pink meat color",
        "concern_level": "moderate",
        "concern_summary": (
            "Crucial for preventing lethal Clostridium botulinum growth in meats, "
            "but can react with amines at high cooking heat to form carcinogenic "
            "nitrosamines. Modest dietary intake is recommended."
        ),
        "evidence_source": "IARC Monograph 114 (Processed Meat); EFSA 2017 Nitrite Opinion",
        "regulatory_status": "Approved with strictly monitored residual limits worldwide",
        "recommendation": (
            "Moderate consumption of cured/processed meats and avoid charring."
        ),
    },
    {
        "id": "sodium-nitrate",
        "name": "Sodium Nitrate",
        "e_number": "E251",
        "synonyms": [
            "sodium nitrate",
            "e251",
            "e-251",
            "ins 251",
            "chile saltpeter",
        ],
        "purpose": "Preservative and curing salt in dry cured meats and hard cheeses",
        "concern_level": "moderate",
        "concern_summary": (
            "Converts in vivo to nitrite, potentially participating in endogenous "
            "nitrosamine formation upon sustained high intake."
        ),
        "evidence_source": "EFSA Scientific Opinion on the Re-evaluation of Sodium Nitrate",
        "regulatory_status": "Approved with regulatory maximum limits (EU, US, Codex)",
        "recommendation": (
            "Enjoy cured meats in moderation as part of a balanced diet."
        ),
    },
    {
        "id": "red-40",
        "name": "Red 40 (Allura Red AC)",
        "e_number": "E129",
        "synonyms": [
            "red 40",
            "allura red",
            "allura red ac",
            "fd&c red no. 40",
            "e129",
            "e-129",
            "ins 129",
            "ci 16035",
        ],
        "purpose": "Synthetic azo dye providing vibrant red coloration",
        "concern_level": "moderate",
        "concern_summary": (
            "Associated in clinical trials (Southampton study) with hyperactivity "
            "in sensitive children. May also trigger mild allergic reactions."
        ),
        "evidence_source": "Lancet Southampton Study (2007); EFSA Regulation (EC) 1333/2008",
        "regulatory_status": "Approved in US; requires hyperactivity warning label in EU",
        "recommendation": (
            "Consider dye-free or naturally colored alternatives for sensitive children."
        ),
    },
    {
        "id": "yellow-5",
        "name": "Yellow 5 (Tartrazine)",
        "e_number": "E102",
        "synonyms": [
            "yellow 5",
            "tartrazine",
            "fd&c yellow no. 5",
            "e102",
            "e-102",
            "ins 102",
            "ci 19140",
        ],
        "purpose": "Synthetic azo dye delivering bright lemon-yellow coloring",
        "concern_level": "moderate",
        "concern_summary": (
            "Known to provoke hypersensitivity reactions (urticaria, asthma flare-ups) "
            "in aspirin-sensitive individuals, and linked to pediatric hyperactivity."
        ),
        "evidence_source": "EFSA Panel on Dietetic Products, Nutrition and Allergies; FDA CFR",
        "regulatory_status": "Permitted in US (mandatory label declaration); warning required in EU",
        "recommendation": (
            "Check labels if you have aspirin sensitivity or allergies to food dyes."
        ),
    },
    {
        "id": "yellow-6",
        "name": "Yellow 6 (Sunset Yellow FCF)",
        "e_number": "E110",
        "synonyms": [
            "yellow 6",
            "sunset yellow",
            "sunset yellow fcf",
            "fd&c yellow no. 6",
            "e110",
            "e-110",
            "ins 110",
            "ci 15985",
        ],
        "purpose": "Synthetic azo dye producing golden yellow/orange color",
        "concern_level": "moderate",
        "concern_summary": (
            "Part of the 'Southampton six' dyes linked to hyperactive behavioral "
            "changes in children and occasional atopic sensitivity."
        ),
        "evidence_source": "EFSA Scientific Opinion on the Re-evaluation of Sunset Yellow FCF",
        "regulatory_status": "Approved with ADI reduction; warning label required in EU",
        "recommendation": (
            "Look for natural food colorings like beta-carotene, annatto, or paprika."
        ),
    },
    {
        "id": "bha",
        "name": "BHA (Butylated Hydroxyanisole)",
        "e_number": "E320",
        "synonyms": [
            "bha",
            "butylated hydroxyanisole",
            "e320",
            "e-320",
            "ins 320",
        ],
        "purpose": "Synthetic antioxidant preventing rancidity in fats, oils, and cereals",
        "concern_level": "moderate",
        "concern_summary": (
            "Classified as reasonably anticipated to be a human carcinogen by the US "
            "National Toxicology Program based on rodent forestomach tumors, though "
            "dietary human levels remain approved."
        ),
        "evidence_source": "US NTP 15th Report on Carcinogens; EFSA ANS Panel (2011)",
        "regulatory_status": "Approved with tight maximum use thresholds (FDA 21 CFR, EU)",
        "recommendation": (
            "Limit frequent consumption of packaged snacks with synthetic BHA."
        ),
    },
    {
        "id": "bht",
        "name": "BHT (Butylated Hydroxytoluene)",
        "e_number": "E321",
        "synonyms": [
            "bht",
            "butylated hydroxytoluene",
            "e321",
            "e-321",
            "ins 321",
        ],
        "purpose": "Synthetic antioxidant extending fat freshness in foods and packaging",
        "concern_level": "moderate",
        "concern_summary": (
            "High experimental dosages in animal studies caused liver enlargement; "
            "safe at current low trace dietary exposures, but synthetic nature draws caution."
        ),
        "evidence_source": "EFSA Scientific Opinion on BHT; JECFA Evaluation",
        "regulatory_status": "Approved with established ADI of 0.25 mg/kg bw/day",
        "recommendation": (
            "Prefer foods preserved with natural antioxidants like vitamin E (tocopherols)."
        ),
    },
    {
        "id": "aspartame",
        "name": "Aspartame",
        "e_number": "E951",
        "synonyms": [
            "aspartame",
            "e951",
            "e-951",
            "ins 951",
            "nutrasweet",
            "equal",
        ],
        "purpose": "Low-calorie intense artificial sweetener (200x sweetness of sugar)",
        "concern_level": "moderate",
        "concern_summary": (
            "Classified as Group 2B (possibly carcinogenic) by WHO/IARC in 2023, "
            "while JECFA and the FDA confirmed the ADI (40-50 mg/kg bw/day) remains safe. "
            "Contraindicated for individuals with phenylketonuria (PKU)."
        ),
        "evidence_source": "WHO IARC / JECFA Joint Statement (July 2023); US FDA Guidance",
        "regulatory_status": "Approved worldwide within ADI; mandatory PKU warning on packaging",
        "recommendation": (
            "Safe within recommended daily intake; avoid if diagnosed with PKU."
        ),
    },
    {
        "id": "acesulfame-potassium",
        "name": "Acesulfame Potassium (Ace-K)",
        "e_number": "E950",
        "synonyms": [
            "acesulfame potassium",
            "acesulfame k",
            "ace k",
            "ace-k",
            "e950",
            "e-950",
            "ins 950",
        ],
        "purpose": "Heat-stable non-caloric high-intensity sweetener",
        "concern_level": "moderate",
        "concern_summary": (
            "Excreted mostly unchanged by kidneys; persistent in aquatic environments. "
            "Safety debates surround trace breakdown products (acetoacetamide), though "
            "regulatory bodies reaffirm safety within the ADI."
        ),
        "evidence_source": "EFSA Re-evaluation of Acesulfame K; US FDA 21 CFR 172.800",
        "regulatory_status": "Approved with ADI of 0-9 mg/kg bw/day (EU) and 15 mg/kg bw/day (US)",
        "recommendation": (
            "Consume in moderation as an occasional sugar substitute."
        ),
    },
    {
        "id": "sucralose",
        "name": "Sucralose",
        "e_number": "E955",
        "synonyms": [
            "sucralose",
            "e955",
            "e-955",
            "ins 955",
            "splenda",
        ],
        "purpose": "Zero-calorie artificial sweetener synthesized from chlorinated sucrose",
        "concern_level": "moderate",
        "concern_summary": (
            "Widely approved within ADI (5 mg/kg bw/day). However, heating above 120°C "
            "may generate chlorinated breakdown products (chloropropanols), and recent "
            "studies explore impacts on gut microbiome diversity."
        ),
        "evidence_source": "German Federal Institute for Risk Assessment (BfR, 2019); US FDA",
        "regulatory_status": "Approved globally; agencies advise avoiding high-heat cooking",
        "recommendation": (
            "Safe for cold foods and beverages within ADI; avoid baking at high temperatures."
        ),
    },
    {
        "id": "sodium-benzoate",
        "name": "Sodium Benzoate",
        "e_number": "E211",
        "synonyms": [
            "sodium benzoate",
            "benzoate of soda",
            "e211",
            "e-211",
            "ins 211",
        ],
        "purpose": "Antimicrobial preservative in acidic soft drinks, jams, and condiments",
        "concern_level": "moderate",
        "concern_summary": (
            "Safe on its own within established limits (ADI 5 mg/kg bw/day). However, "
            "when combined with ascorbic acid (vitamin C) under heat or light, it can "
            "form trace benzene, a known human carcinogen."
        ),
        "evidence_source": "US FDA Beverage Guidance on Benzene; EFSA ANS Panel (2016)",
        "regulatory_status": "Approved with strict maximum concentration limits (<= 0.1%)",
        "recommendation": (
            "Avoid drinks that combine sodium benzoate and ascorbic acid (vitamin C)."
        ),
    },
    {
        "id": "high-fructose-corn-syrup",
        "name": "High Fructose Corn Syrup (HFCS)",
        "e_number": None,
        "synonyms": [
            "high fructose corn syrup",
            "hfcs",
            "hfcs-55",
            "hfcs-42",
            "glucose-fructose syrup",
            "isoglucose",
        ],
        "purpose": "Liquid caloric sweetener offering sweetness, humectancy, and browning",
        "concern_level": "moderate",
        "concern_summary": (
            "High dietary intake supplies readily absorbed free fructose, which is "
            "metabolized primarily in the liver and strongly linked to non-alcoholic "
            "fatty liver disease (NAFLD), insulin resistance, and visceral adiposity."
        ),
        "evidence_source": "American Heart Association Scientific Advisory; NIH Studies",
        "regulatory_status": "Approved food ingredient; dietary guidelines urge minimizing intake",
        "recommendation": (
            "Minimize consumption of sweetened beverages and ultra-processed foods containing HFCS."
        ),
    },
    {
        "id": "carrageenan",
        "name": "Carrageenan",
        "e_number": "E407",
        "synonyms": [
            "carrageenan",
            "e407",
            "e-407",
            "ins 407",
            "chondrus extract",
            "irish moss extract",
        ],
        "purpose": "Thickener, stabilizer, and plant-based gelling agent in dairy and alternatives",
        "concern_level": "moderate",
        "concern_summary": (
            "Food-grade undegraded carrageenan is permitted, but its degraded variant "
            "(poligeenan) induces gastrointestinal inflammation and ulceration in animal models. "
            "Some individuals report digestive distress."
        ),
        "evidence_source": "JECFA Evaluation Series; EFSA Re-evaluation of Carrageenan",
        "regulatory_status": "Approved for general foods; restricted in infant formula in the EU",
        "recommendation": (
            "Those with sensitive digestive systems may benefit from carrageenan-free alternatives."
        ),
    },
    {
        "id": "caramel-color-iv",
        "name": "Caramel Color IV (Sulfite Ammonia Caramel)",
        "e_number": "E150d",
        "synonyms": [
            "caramel color iv",
            "caramel colour iv",
            "caramel color class iv",
            "ammonia sulphite caramel",
            "e150d",
            "e-150d",
            "ins 150d",
            "caramel iv",
        ],
        "purpose": "Deep brown coloring in colas, dark beers, gravies, and pet food",
        "concern_level": "moderate",
        "concern_summary": (
            "Manufacturing with ammonia compounds can produce 4-methylimidazole (4-MEI), "
            "a compound classified by IARC as possibly carcinogenic (Group 2B). Strict "
            "residual 4-MEI limits are enforced."
        ),
        "evidence_source": "IARC Monograph 101; EFSA Scientific Opinion on Caramel Colours",
        "regulatory_status": "Permitted with strict maximum 4-MEI limits; California Prop 65 warning",
        "recommendation": (
            "Choose beverages that limit artificial caramel coloring or meet low 4-MEI standards."
        ),
    },

    # ---------------- SAFE / LOW CONCERN ----------------
    {
        "id": "citric-acid",
        "name": "Citric Acid",
        "e_number": "E330",
        "synonyms": [
            "citric acid",
            "e330",
            "e-330",
            "ins 330",
        ],
        "purpose": "Natural acidity regulator, flavor enhancer, and antioxidant synergist",
        "concern_level": "low",
        "concern_summary": (
            "An organic acid naturally abundant in lemons, limes, and oranges, and an "
            "essential intermediate in human cellular respiration (the Krebs cycle). "
            "Fully metabolized with an outstanding safety profile."
        ),
        "evidence_source": "FDA GRAS 21 CFR 184.1033; JECFA ADI Not Specified",
        "regulatory_status": "Approved worldwide with quantum satis (unrestricted safe) status",
        "recommendation": (
            "Completely safe for regular consumption. Rinse mouth after sour foods to protect dental enamel."
        ),
    },
    {
        "id": "ascorbic-acid",
        "name": "Ascorbic Acid (Vitamin C)",
        "e_number": "E300",
        "synonyms": [
            "ascorbic acid",
            "vitamin c",
            "e300",
            "e-300",
            "ins 300",
            "l-ascorbic acid",
        ],
        "purpose": "Antioxidant nutrient preventing discoloration and flour oxidation",
        "concern_level": "low",
        "concern_summary": (
            "An essential water-soluble vitamin vital for immune function, collagen synthesis, "
            "and antioxidant protection. Prevents food browning without any toxic risk."
        ),
        "evidence_source": "US National Academy of Medicine; EFSA Panel on Dietetic Products",
        "regulatory_status": "Approved worldwide as a beneficial nutrient and food additive",
        "recommendation": (
            "Safe and nutritionally beneficial."
        ),
    },
    {
        "id": "soy-lecithin",
        "name": "Soy Lecithin",
        "e_number": "E322",
        "synonyms": [
            "soy lecithin",
            "lecithin",
            "sunflower lecithin",
            "e322",
            "e-322",
            "ins 322",
        ],
        "purpose": "Natural phospholipid emulsifier preventing phase separation in chocolate and spreads",
        "concern_level": "low",
        "concern_summary": (
            "A natural mixture of phospholipids naturally present in cell membranes, egg yolks, "
            "and soybeans. Completely safe and non-toxic for the general population. Note "
            "allergen origin for individuals with severe soy hypersensitivity."
        ),
        "evidence_source": "FDA GRAS 21 CFR 184.1400; EFSA ANS Panel Re-evaluation",
        "regulatory_status": "Approved globally without quantitative limitation",
        "recommendation": (
            "Safe to consume regularly; verify source if allergic to soy."
        ),
    },
    {
        "id": "xanthan-gum",
        "name": "Xanthan Gum",
        "e_number": "E415",
        "synonyms": [
            "xanthan gum",
            "e415",
            "e-415",
            "ins 415",
        ],
        "purpose": "Plant-based thickener, stabilizer, and binder for gluten-free baking",
        "concern_level": "low",
        "concern_summary": (
            "A soluble fermentation polysaccharide derived from simple sugars. Acts as "
            "dietary fiber and passes safely through the digestive tract without absorption. "
            "Very high single intakes may produce mild, harmless laxative effects."
        ),
        "evidence_source": "EFSA Scientific Opinion on the Re-evaluation of Xanthan Gum (2017)",
        "regulatory_status": "Approved worldwide with GRAS status",
        "recommendation": (
            "Safe to consume. Helpful for texture in gluten-free products."
        ),
    },
    {
        "id": "guar-gum",
        "name": "Guar Gum",
        "e_number": "E412",
        "synonyms": [
            "guar gum",
            "e412",
            "e-412",
            "ins 412",
        ],
        "purpose": "Natural thickening dietary fiber derived from guar beans",
        "concern_level": "low",
        "concern_summary": (
            "A natural galactomannan polysaccharide extracted from the seeds of Cyamopsis "
            "tetragonoloba. Acts as beneficial prebiotic fiber supporting normal digestion."
        ),
        "evidence_source": "EFSA 2017 Re-evaluation of Guar Gum; US FDA GRAS Affirmation",
        "regulatory_status": "Approved worldwide for general food use",
        "recommendation": (
            "Safe and natural thickener providing soluble dietary fiber."
        ),
    },
    {
        "id": "pectin",
        "name": "Pectin",
        "e_number": "E440",
        "synonyms": [
            "pectin",
            "fruit pectin",
            "citrus pectin",
            "apple pectin",
            "e440",
            "e-440",
            "ins 440",
        ],
        "purpose": "Natural fruit fiber gelling agent in jams, jellies, and fruit spreads",
        "concern_level": "low",
        "concern_summary": (
            "Extracted from apple pomace and citrus peels. Recognized worldwide as a safe "
            "soluble dietary fiber with well-documented cardiovascular and cholesterol-lowering benefits."
        ),
        "evidence_source": "JECFA Evaluation (ADI 'Not Specified'); EFSA ANS Panel (2017)",
        "regulatory_status": "Approved globally with unconditional safety status",
        "recommendation": (
            "Safe and naturally nutritious dietary fiber."
        ),
    },
    {
        "id": "calcium-propionate",
        "name": "Calcium Propionate",
        "e_number": "E282",
        "synonyms": [
            "calcium propionate",
            "e282",
            "e-282",
            "ins 282",
        ],
        "purpose": "Anti-mold preservative extending the freshness of bread and baked goods",
        "concern_level": "low",
        "concern_summary": (
            "Calcium salt of propionic acid, an organic fatty acid naturally synthesized by "
            "human gut microbiota and found in Swiss cheeses. Fully metabolized into water and CO2."
        ),
        "evidence_source": "US FDA 21 CFR 184.1221; EFSA 2014 Safety Re-evaluation",
        "regulatory_status": "Approved globally (GRAS in USA, permitted across the EU)",
        "recommendation": (
            "Safe preservative that prevents harmful mold and bacterial spoilage in breads."
        ),
    },
    {
        "id": "monosodium-glutamate",
        "name": "Monosodium Glutamate (MSG)",
        "e_number": "E621",
        "synonyms": [
            "monosodium glutamate",
            "msg",
            "e621",
            "e-621",
            "ins 621",
            "sodium glutamate",
        ],
        "purpose": "Savory umami flavor enhancer (sodium salt of common glutamic acid)",
        "concern_level": "low",
        "concern_summary": (
            "Glutamate is one of the most abundant amino acids in nature and in human "
            "proteins, occurring naturally in aged cheeses, tomatoes, and mushrooms. Rigorous "
            "double-blind clinical trials find no evidence linking MSG to chronic toxicity or "
            "reproducible 'MSG symptom complex' in the general population."
        ),
        "evidence_source": "US FDA Comprehensive Review on MSG; EFSA 2017 Glutamates Safety Re-evaluation",
        "regulatory_status": "Approved globally (FDA GRAS, EFSA ADI 30 mg/kg bw/day)",
        "recommendation": (
            "Safe for the general public. Helps lower total recipe sodium by intensifying flavor."
        ),
    },
    {
        "id": "propylene-glycol",
        "name": "Propylene Glycol",
        "e_number": "E1520",
        "synonyms": [
            "propylene glycol",
            "e1520",
            "e-1520",
            "ins 1520",
            "1,2-propanediol",
        ],
        "purpose": "Humectant, flavoring carrier, and moisture maintainer",
        "concern_level": "low",
        "concern_summary": (
            "Rapidly converted in the liver into lactic acid and pyruvic acid (normal cellular "
            "metabolites). Often falsely confused with toxic industrial ethylene glycol; food-grade "
            "propylene glycol is non-toxic at approved dietary usage levels."
        ),
        "evidence_source": "US FDA 21 CFR 184.1666; ATSDR Toxicological Profile",
        "regulatory_status": "Approved with GRAS status in US, approved in EU for flavors",
        "recommendation": (
            "Safe within approved dietary limits."
        ),
    },
    {
        "id": "sodium-erythorbate",
        "name": "Sodium Erythorbate",
        "e_number": "E316",
        "synonyms": [
            "sodium erythorbate",
            "e316",
            "e-316",
            "ins 316",
        ],
        "purpose": "Antioxidant and meat cure accelerator that helps prevent nitrosamine formation",
        "concern_level": "low",
        "concern_summary": (
            "A stereoisomer of vitamin C that accelerates the curing process and actively "
            "inhibits the formation of nitrosamines in cured meats. Safe and non-toxic."
        ),
        "evidence_source": "US FDA 21 CFR 182.3041; EFSA ANS Panel (2016)",
        "regulatory_status": "Approved globally",
        "recommendation": (
            "Safe functional antioxidant that actively reduces nitrosamine formation."
        ),
    },
    {
        "id": "potassium-sorbate",
        "name": "Potassium Sorbate",
        "e_number": "E202",
        "synonyms": [
            "potassium sorbate",
            "e202",
            "e-202",
            "ins 202",
            "sorbate",
        ],
        "purpose": "Antimicrobial and anti-fungal preservative inhibiting molds and yeasts",
        "concern_level": "low",
        "concern_summary": (
            "Salt of sorbic acid that metabolizes cleanly in the human body into water and "
            "carbon dioxide via the beta-oxidation fatty acid pathway. Well tolerated."
        ),
        "evidence_source": "EFSA 2015 Re-evaluation of Sorbic Acid; US FDA GRAS",
        "regulatory_status": "Approved globally with ADI of 11 mg/kg bw/day",
        "recommendation": (
            "Safe preservative protecting fruit products, cheeses, and beverages from mold."
        ),
    },
]


_SYNONYM_LOOKUP: dict[str, dict[str, Any]] = {}
for _additive in CURATED_ADDITIVES:
    for _syn in _additive["synonyms"]:
        _SYNONYM_LOOKUP[_syn.lower()] = _additive


def get_curated_additives(
    concern_level: ConcernLevel | None = None,
    query: str | None = None,
) -> list[dict[str, Any]]:
    """Return the curated list of additives with optional filtering."""
    results = CURATED_ADDITIVES
    if concern_level is not None:
        results = [a for a in results if a["concern_level"] == concern_level]
    if query:
        q = query.strip().lower()
        results = [
            a
            for a in results
            if q in a["name"].lower()
            or (a.get("e_number") and q in a["e_number"].lower())
            or q in a["purpose"].lower()
            or any(q in syn.lower() for syn in a["synonyms"])
        ]
    return results


def _clean_token(text: str) -> str:
    """Normalize text for matching: lower, strip non-alphanumeric except spaces/hyphens."""
    return re.sub(r"[^\w\s\-]", " ", text.lower()).strip()


def _extract_parenthetical_segments(text: str) -> list[str]:
    """Extract nested segments inside parentheses/brackets as well as outer text."""
    segments = [text]
    # Find all items inside parentheses or brackets
    nested = re.findall(r"[\(\[](.*?)[\)\]]", text)
    for group in nested:
        # Split by comma inside the parentheses too
        sub_items = [part.strip() for part in group.split(",") if part.strip()]
        segments.extend(sub_items)
    return segments


def _match_additive_in_text(raw_phrase: str) -> list[dict[str, Any]]:
    """Match any curated additive against a single raw ingredient phrase."""
    matched: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    # Test raw and cleaned segments
    segments = _extract_parenthetical_segments(raw_phrase)

    for segment in segments:
        cleaned_segment = _clean_token(segment)
        if not cleaned_segment:
            continue

        for additive in CURATED_ADDITIVES:
            if additive["id"] in seen_ids:
                continue

            for syn in additive["synonyms"]:
                syn_clean = _clean_token(syn)
                # Word-boundary check: syn must appear as a discrete phrase or word
                pattern = rf"(?<!\w){re.escape(syn_clean)}(?!\w)"
                if re.search(pattern, cleaned_segment):
                    matched.append(additive)
                    seen_ids.add(additive["id"])
                    break

    return matched


def detect_additives(
    ingredients: list[str] | str | None,
) -> dict[str, Any]:
    """
    Identify selected additives and ingredients from the curated knowledge base.

    - Returns matched additives with functional purpose, concern level, and evidence.
    - Categorizes concern levels objectively (high, moderate, low/safe).
    - Preserves unmatched natural ingredients.
    - Provides a balanced educational guidance statement to avoid calling every additive harmful.
    """
    if ingredients is None:
        ingredient_list: list[str] = []
    elif isinstance(ingredients, str):
        # Split on commas taking nesting into account if possible
        raw_list = [part.strip() for part in re.split(r",(?![^\(\[]*[\)\]])", ingredients) if part.strip()]
        ingredient_list = raw_list if raw_list else ([ingredients.strip()] if ingredients.strip() else [])
    else:
        ingredient_list = [str(item).strip() for item in ingredients if str(item).strip()]

    matched_additives: list[dict[str, Any]] = []
    seen_additive_ids: set[str] = set()
    unmatched_ingredients: list[str] = []

    for item in ingredient_list:
        found_in_item = _match_additive_in_text(item)
        if found_in_item:
            for additive in found_in_item:
                if additive["id"] not in seen_additive_ids:
                    seen_additive_ids.add(additive["id"])
                    matched_additives.append(
                        {
                            **additive,
                            "detected_in_ingredient": item,
                        }
                    )
        else:
            unmatched_ingredients.append(item)

    # Count breakdown by concern level
    high_count = sum(1 for a in matched_additives if a["concern_level"] == "high")
    moderate_count = sum(1 for a in matched_additives if a["concern_level"] == "moderate")
    low_count = sum(1 for a in matched_additives if a["concern_level"] == "low")

    if high_count > 0:
        overall_concern = "high"
    elif moderate_count > 0:
        overall_concern = "moderate"
    elif low_count > 0:
        overall_concern = "low"
    else:
        overall_concern = "none_detected"

    # Sort matched additives: high concern first, then moderate, then low
    concern_order = {"high": 0, "moderate": 1, "low": 2}
    matched_additives.sort(key=lambda a: concern_order.get(a["concern_level"], 99))

    return {
        "total_ingredients_scanned": len(ingredient_list),
        "total_additives_detected": len(matched_additives),
        "overall_concern": overall_concern,
        "counts": {
            "high": high_count,
            "moderate": moderate_count,
            "low": low_count,
        },
        "matched_additives": matched_additives,
        "unmatched_ingredients": unmatched_ingredients,
        "guidance_note": (
            "Food additives serve important functions including preservation, "
            "texture stabilization, and safety against dangerous foodborne pathogens. "
            "Not every additive is harmful. Label Lens distinguishes evidence-based concern "
            "levels according to evaluations by the EFSA, FDA, WHO/JECFA, and scientific consensus."
        ),
    }
