# Product Requirements Document
## DataHacks 2026 — Entrepreneurship Track
**Team:** [Your Team Name]
**Event:** DataHacks 2026, UCSD | April 18–19, 2026 (36 hours)
**Track:** Entrepreneurship
**Last updated:** April 17, 2026

---

## 1. Problem Statement
> *To be finalized once theme drops — fill in the blank:*

**"[TARGET USER] struggle to [PAIN POINT], costing them [TIME/MONEY/OPPORTUNITY]. Existing solutions fail because [GAP]. We fix this with a data-driven tool that [YOUR SOLUTION]."**

---

## 2. Product Overview

An AI-powered data analysis web app that takes real-world data, surfaces business-critical insights via a trained ML model, and translates findings into actionable startup strategy using an LLM layer — all in a clean, live-demo-ready interface.

**Why it wins:** Most DS teams submit a Jupyter notebook. We ship a product.

---

## 3. Target User

| Attribute | Detail |
|---|---|
| Who | [To fill in after theme — e.g. small business owners, city planners, HR managers] |
| Pain | Manual, slow, or non-existent data analysis |
| Goal | Make better decisions faster |
| Willingness to pay | [To fill in — e.g. $X/month SaaS] |

---

## 4. Core Features (MVP)

### F1 — Data Ingestion
- CSV file upload
- Sample dataset loader (fallback if no data available)
- Auto-detects column types (numeric vs categorical)
- **Priority:** P0 — nothing works without this

### F2 — EDA Dashboard
- Auto-generated distribution charts
- Correlation heatmap
- Interactive scatter plot with color grouping
- **Priority:** P0 — needed for the "insight" narrative

### F3 — ML Model Pipeline
- Switchable between Classification and Regression
- Random Forest with feature importance output
- Train/test split with performance metrics (accuracy / R² / MAE)
- **Priority:** P0 — core technical credibility

### F4 — AI Insight Generator ⭐ Differentiator
- Sends model results + problem context to Claude API
- Returns: Key insight, top opportunity, risk, next steps, pitch hook
- One-click generate, downloadable output
- **Priority:** P0 — this is the demo moment

### F5 — Pitch Summary Tab
- Auto-populates from all prior tabs
- Editable vision statement
- Judge-ready one-pager layout
- **Priority:** P1 — polish, not bloat

---

## 5. Out of Scope (for this hackathon)

- User authentication / accounts
- Database persistence
- Mobile responsiveness
- Real-time data streaming
- Production deployment / scaling

---

## 6. Tech Stack

| Layer | Tool |
|---|---|
| Frontend / App | Streamlit |
| Data processing | pandas, numpy |
| ML | scikit-learn (Random Forest) |
| Visualization | Plotly Express |
| AI Insights | Anthropic Claude API (claude-sonnet-4) |
| Environment | Python 3.10+ |

---

## 7. Team & Ownership

| Role | Owner | Responsibilities |
|---|---|---|
| Demo Lead | [Name] | App UI polish, pitch delivery, 3-min demo rehearsal |
| Data & Model | [Name] | Dataset sourcing, cleaning, model training, metrics |
| Story & Strategy | [Name] | Problem statement, business case, AI insight editing |
| Glue Engineer | [Name] | Integration, bug fixes, API setup, deployment |

---

## 8. Timeline

| Time | Milestone |
|---|---|
| Hour 0 | Theme announced — pick concept, lock dataset |
| Hour 1 | Dataset loaded into app, EDA running |
| Hour 3 | Model trained, feature importance visible |
| Hour 5 | AI Insights generated, pitch narrative drafted |
| Hour 8 | **Full demo rehearsal #1** |
| Hour 10 | Feature freeze — polish only |
| Hour 12 | **Full demo rehearsal #2** |
| Submission | Devpost submitted, app live |

---

## 9. Success Metrics (Judging Criteria)

Based on DataHacks entrepreneurship track + VC judge priorities:

| Criteria | How we address it |
|---|---|
| **Real problem** | Problem statement anchored to a real user + market |
| **Data-driven insight** | EDA + ML model surfaces non-obvious finding |
| **Business viability** | AI Insights tab outputs monetization angle |
| **Demo quality** | Live Streamlit app, no slides-only pitch |
| **Novelty** | LLM insight layer differentiates from pure DS teams |

---

## 10. Demo Script (3 minutes)

1. **Hook (20s):** "Every year, [WHO] loses [X] because of [PROBLEM]. We built a tool that fixes this in seconds."
2. **Show the data (30s):** Load dataset live, point to one key chart.
3. **Run the model (30s):** Train, show accuracy + top feature.
4. **AI Insights (60s):** Hit generate — read the pitch hook out loud. Let judges react.
5. **Business case (30s):** "Our customer is X, they pay Y, our edge is Z."
6. **Close (10s):** "This is [Product Name]. Let's build it."

---

## 11. Contingency Plans

| Risk | Mitigation |
|---|---|
| Theme doesn't fit our concepts | All 6 concepts are adaptable — pick closest, rename |
| Dataset is hard to find | Pre-download 2-3 Kaggle datasets tonight as backup |
| API key fails | Pre-generate and cache 1 sample insight output |
| Model performs poorly | Frame it honestly — "early signal, here's what we'd do with more data" |
| Demo crashes | Screenshot backup of every tab ready to paste |
