# Label Lens

AI-powered food label analysis, nutrition evaluation, and evidence-based additive detection.

---

## Features

### 1. Harmful Additive & Ingredient Detection
- **Curated Knowledge Base**: Vetted catalog of common food additives and ingredients with functional roles, peer-reviewed scientific findings, and global regulatory statuses (EFSA, US FDA, WHO/JECFA).
- **Evidence-Based Concern Levels**:
  - **High Concern**: Compounds with substantiated genotoxicity, carcinogenicity, or regulatory bans (e.g., Potassium Bromate, Titanium Dioxide, Brominated Vegetable Oil, Partially Hydrogenated Oils).
  - **Moderate Concern**: Additives with pediatric hyperactivity warnings, sensitivity reactions, or specific Acceptable Daily Intake (ADI) limitations (e.g., Red 40, Yellow 5, Aspartame, Sodium Benzoate, BHA/BHT).
  - **Safe / Low Concern / Functional**: Functional compounds that are safe and non-toxic (e.g., Citric Acid, Ascorbic Acid / Vitamin C, Soy Lecithin, Xanthan Gum, Calcium Propionate, MSG).
- **Non-Alarmist Scientific Principle**: Additives serve vital food preservation and safety purposes. Label Lens avoids labeling every additive as harmful, distinguishing necessary preservatives from controversial compounds.
- **Quick Preset Testing**: One-click presets to test real-world packaged foods (bakery dough conditioners, citrus beverages, confectionery, clean-label granola).

### 2. Nutrition Breakdown
- Calculates nutrient contributions (sugar, sodium, saturated fat) against daily reference thresholds.
- Supports both **per-serving** and **per-100g** basis.
- Converts grams of sugar to visual teaspoon equivalents (~4 g/tsp).

### 3. Additive Knowledge Base Explorer
- Searchable and filterable encyclopedia of food additives.
- Filter by concern level or search by common name, E-number, or functional purpose.

### 4. Label OCR Text Extraction
- Local OCR via Tesseract and Pillow (supporting JPEG, PNG, and WebP up to 10 MiB).
- Preserves all review-required flags without reporting artificial confidence numbers.

---

## Tech Stack

- **Backend**: Python 3.10+, FastAPI, Pydantic v2, Pillow, PyTesseract, Pytest
- **Frontend**: React 19, Vite, Vanilla CSS design system, Oxlint

---

## Getting Started

### Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Or `.venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Run backend test suite:
```bash
pytest
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Run frontend lint & build:
```bash
npm run lint
npm run build
```

---

## API Endpoints

- `GET /health`: Health check status.
- `GET /additives/knowledge-base`: Retrieve curated additives (supports `concern_level` and `query` parameters).
- `POST /analyze/ingredients`: Scan ingredients list or text for additives and evidence-based concern levels.
- `POST /analyze/nutrition`: Assess sugar, sodium, and saturated fat against daily reference limits.
- `POST /extract/label`: Upload food label images to extract text and candidate fields via local OCR.
