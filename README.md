# aera_2026

Research materials for **AERA 2026**: AI-assisted scoring of elementary science constructed responses using a **multi-agent grading framework**.

## What task we do

We grade student answers to **Unit 4.1 Question 6 (Q6)** from a dynamic Earth/geology performance task.

**Prompt to students:** Look closely at the photo. Think about a system that has parts that work together. Identify two or three parts of a system and explain how they work together to cause change over time.

**Scoring scale:** 0–3, based on a rubric that looks for:

- identification of land-system parts (e.g., mountains, rivers, rock, vegetation)
- explanation of how those parts interact
- evidence of change over time (weathering, erosion, plate movement, etc.)

Each student response is graded by **five independent AI agents**. Their scores are combined with consensus rules and compared against **two human expert grades** when running batch analysis in `main.py`.

## Multi-agent grading framework

```text
Student answer
      │
      ├── Agent 1 (rubric prompt variant 1) ──► grade + explanation
      ├── Agent 2 (rubric prompt variant 2) ──► grade + explanation
      ├── Agent 3 (rubric prompt variant 3) ──► grade + explanation
      ├── Agent 4 (rubric prompt variant 4) ──► grade + explanation
      └── Agent 5 (rubric prompt variant 5) ──► grade + explanation
                          │
                          ▼
              Consensus & agreement metrics
```

### Design choices

1. **Five parallel graders** — Each agent uses a different rubric prompt from `prompts.py` (`base_prompt1` … `base_prompt5`). All agents see the same student answer but may interpret the rubric differently, similar to multiple human raters.

2. **Structured output** — Each agent returns a numeric grade (0–3) and a short explanation aligned to the rubric.

3. **Ensemble decision rules**
   - **Majority vote:** most common grade across the five agents
   - **Agent agree:** at least 4 of 5 agents give the same grade
   - **Agent unanimous:** all 5 agents give the same grade
   - **Consensus grade:** the shared grade when ≥4 agents agree; otherwise `None`

4. **Expert comparison (batch mode)** — `main.py` also records two human expert grades per response and reports agreement rates between experts, agents, and both together.

5. **Model** — Google **Gemini 2.5 Flash** via API.

## Repository contents

| Path | Description |
|------|-------------|
| `paper/` | Conference paper and related files |
| `prompts.py` | Five rubric prompt templates for the grading agents |
| `main.py` | Batch grading script for CSV input |
| `ai_grading_demo.ipynb` | Interactive demo on four example student answers |
| `requirements.txt` | Python dependencies |
| `.env` | API key (not committed; create locally) |

## Setup

1. **Clone the repository**

```bash
git clone https://github.com/XunleiGino123/aera_2026.git
cd aera_2026
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

3. **Add your Gemini API key**

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_key_here
```

Optional, if Google APIs are blocked on your network:

```env
HTTPS_PROXY=http://127.0.0.1:7890
```

## How to run it

### Option A — Interactive demo (recommended first)

Open and run `ai_grading_demo.ipynb` in Cursor, VS Code, or Jupyter.

1. Run cells **top to bottom** (the notebook installs requirements automatically).
2. The demo grades **Example 1–4** with all five agents.
3. Review each agent’s explanation, the grade matrix, and consensus summary.

Example answers in the demo:

1. Mountains are on moving earth plates that raise them over time, as they push against each other.
2. The river are running around and shape the terretories of the land gives the envidence of changing over time
3. I do not know
4. They change because it was bright outside, and the water dried up.

```bash
python -m notebook ai_grading_demo.ipynb
```

> **Note:** The demo uses the Gemini **REST API** (HTTPS) for better compatibility with VPN/proxy setups.

### Option B — Batch grading on a CSV

Place your input CSV (default: `U4.1Q6final.csv`) in the project folder, then run:

```bash
# Grade all rows
python main.py

# Grade first 10 rows only
python main.py -n 10

# Custom input/output paths
python main.py --input U4.1Q6final.csv --output geology_q6_87.csv
```

Output is a CSV with student answers, expert grades, each agent’s grade and explanation, and consensus fields.

## Troubleshooting

| Issue | What to try |
|-------|-------------|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` in the same Python environment as your notebook kernel |
| API connection timeout / `503` | Enable VPN or set `HTTPS_PROXY` in `.env` |
| `GEMINI_API_KEY not found` | Create `.env` with your key in the project root |

## Citation

If you use this code or framework, please cite the associated AERA 2026 paper in `paper/`.
