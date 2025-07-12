# Repository Overview – **Jarvis\_BriefMe**

> 💡 **Purpose:** automate a 05:00 AZ daily brief, persist TXT + XLSX under `Outputs/`, and email the body to G.

## 1. Directory Layout

```text
Jarvis_BriefMe/
├── src/
│   ├── main.py               # Orchestrator – supports --dry-run, --email
│   ├── fetchers/
│   │   ├── hn.py             # Hacker News top 10 utility
│   │   ├── yc.py             # YC blog (if needed in future)
│   │   ├── github_trend.py   # Scrape trending MCP
│   │   ├── pbj.py            # Phoenix Business Journal RSS
│   │   ├── notion.py         # Generic Notion helper (transcripts & quiz DBs)
│   │   ├── restcountries.py  # Random country
│   │   ├── oscars.py         # Oscar winners cache
│   │   ├── presidents.py     # US presidents dataset
│   │   ├── inventions.py     # Major inventions by year
│   │   └── misc_facts.py     # WW1/WW2/Europe/… fact pickers
│   ├── generators/
│   │   ├── cycle.py          # DaysLeft / year / state engine (cycles.json)
│   │   ├── summariser.py     # GPT wrapper (OpenAI)
│   │   ├── codebase.py       # Pick + describe odgsully repo
│   │   ├── cs_quiz.py        # Choose CS term & definition
│   │   └── spanish_quiz.py   # Pick Español phrase & inverse
│   ├── template_engine.py    # Jinja2 populate
│   ├── file_writer.py        # TXT & XLSX save helpers
│   ├── emailer.py            # Gmail SMTP send
│   ├── settings.py           # Pydantic env loader
│   └── utils/
│       ├── logger.py         # structlog config
│       └── retry.py          # async retry decorator
├── templates/
│   └── daily_template.txt    # Raw template (verbatim from PRD)
├── Outputs/
│   ├── dailies/              # Daily_*.txt
│   └── tables/               # Table_*.xlsx (+ .gitkeep)
├── tests/
│   ├── __init__.py
│   ├── test_cycle.py
│   ├── test_fetchers.py
│   ├── test_generators.py
│   ├── test_template.py
│   ├── test_file_writer.py
│   └── test_e2e.py
├── docs/
│   ├── PRD.md                # v2 – synced with product spec
│   └── repo_overview.md      # this file
├── requirements.txt
├── Makefile                  # install / lint / test / run / email
├── .env.example
└── .gitignore
```

## 2. Command Cheatsheet

| Command        | Action                                          |
| -------------- | ----------------------------------------------- |
| `make install` | Create venv & install deps (`requirements.txt`) |
| `make run`     | Generate TXT + XLSX to `Outputs/`, **no email** |
| `make email`   | Same as run + SMTP send                         |
| `make test`    | Run pytest w/ coverage gate ≥90 %               |
| `ruff check .` | Static lint                                     |

## 3. Key Modules

- `fetchers/hn.py` – `async def get_top_article()` returns `Article(title,url,text)` best‑matching keywords list.
- `generators/cycle.py` – handles JSON state `{year, state_index, days_left}`; exposes `advance()` returning today's triplet.
- `file_writer.py` – `write_daily_txt(context)` and `update_table_xlsx(context)`.
- `main.py` – glues everything: gathers `context` dict → template → write → email.

## 4. Environment Variables (`.env`)

```ini
OPENAI_API_KEY=
NOTION_API_KEY=
GMAIL_APP_PASSWORD=
GMAIL_FROM=digest-bot@mycompany.com
GMAIL_TO=gbsullivan@mac.com
GITHUB_TOKEN=
TIMEZONE=America/Phoenix
ROOT_DIR=/Users/garrettsullivan/Desktop/AUTOMATE/Vibe Code/Jarvis_BriefMe
```

## 5. Scheduling (Fly.io Example)

```toml
[[statics]]
  guest = "python src/main.py --email"
  schedule = "0 12 * * *" # 05:00 AZ (UTC‑7)
```

## 6. Testing Highlights

- `test_cycle.py` – asserts 10 successive days produce 3‑2‑1 cycle and year/state rollover.
- `test_e2e.py` – end‑to‑end dry‑run with SMTP mocked by `aiosmtpd` fixture, verifies TXT & XLSX.

## 7. Data Assets

CSV/JSON files live in `src/datasets/` (Oscars.csv, Presidents.csv, Inventions.csv, US_States.json, etc.) and are version‑controlled.

---

### Contributors

- **@odgsully** – product owner
- **Claude Code** – implementation

---

© 2025 Jarvis BriefMe. Released under MIT.