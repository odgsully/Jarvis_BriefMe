# Product Requirements Document (PRD)

## 1 — Objective

Design **Jarvis BriefMe**, an autonomous Python service that assembles a rich, multi‑domain morning brief, saves two files locally (daily TXT & cumulative XLSX) under `Outputs/`, and emails the brief to [**gbsullivan@mac.com**](mailto\:gbsullivan@mac.com) every day at **05:00 America/Phoenix**.

> **North‑Star KPI:** Digest arrives before 05:05 with ≥ 95 % field‑fill success and < 3 unplanned failures/30 days.

---

## 2 — Background & Rationale

G currently hand‑curates disparate signals—YC, HN, GitHub, Phoenix Business Journal, Notion transcript board, geography trivia, Oscars history, global facts, etc. Manual prep is unsustainable. A single Python pipeline with deterministic cycles (state/year) eliminates friction and sets a foundation for future Slack/Notion distribution.

---

## 3 — Template & Placeholder Inventory

The email/TXT body follows the **“New Template”** supplied (see Appendix A). Placeholders fall into three buckets:

| Category           | Placeholders                                                                                                                                                                                                                                                                                                 | Source & Logic                                                                                               |                         |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------ | ----------------------- |
| **Daily Fetched**  | `FULLDATE`, `YC article pick` & derived fields, GitHub trending MCP, PBJ pick & derivatives, Notion transcript table, random “Country of the Day”, `CodebaseToday`, `Current Codebase summary`, WW/Europe/Ireland/Jerusalem/India/Mexico facts, stunt rigging, bike, NASA, GC excerpt, CS term, Español quiz | External APIs / Notion / local Git                                                                           | Refreshed **every day** |
| **Cyclic (3‑day)** | `DaysLeft`, `CurrentStudyYear`, `CurrentStudyState`                                                                                                                                                                                                                                                          | Deterministic cycle engine → `DaysLeft` sequence 3→2→1; advance *year* & *state* when `DaysLeft` resets to 3 |                         |
| **Year‑Bound**     | Oscars winners, US President/VP, presidential decision, major invention, launch fact                                                                                                                                                                                                                         | Derived from `CurrentStudyYear` via local datasets                                                           |                         |

A full mapping with data paths, rate limits, and GPT prompts is in Table 1 (appendix B).

---

## 4 — Scope

### In‑Scope

1. **Fetch & transform** all fields per mapping table.
2. **Cycle engine** maintaining persistent JSON (`cycles.json`) to track current year, state, and DaysLeft.
3. **Template rendering** with Jinja2, producing:
   - `Outputs/dailies/Daily_<MM.DD.YY>.txt` (plain‑text body)
   - `Outputs/tables/Table_<MM.DD.YY>.xlsx` (persisting cumulative structured data; new row per day).
4. **Email dispatch** via Gmail SMTP (App Password) at 05:00.
5. Robust **tests** ≥ 90 % coverage.

### Out of Scope (v2)

- Slack / Notion push.
- GUI dashboard.

---

## 5 — High‑Level Flow

```mermaid
graph TD
  Cron[05:00 cron] --> Main(main.py)
  Main --> Fetch[Fetch stage (async)]
  Fetch --> GPT[Summarise / generate]
  GPT --> CycleEngine[Load & advance cycles.json]
  CycleEngine --> Template[Render Jinja2]
  Template --> Files[Write TXT + update XLSX]
  Files --> Email[SMTP send]
  Email --> Log[structlog JSON logs]
```

---

## 6 — Functional Requirements

| ID        | Requirement                                                                                                                                            | Priority |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | -------- |
| **FR‑1**  | Scheduler triggers daily at 05:00 America/Phoenix.                                                                                                     | P0       |
| **FR‑2**  | Retrieve top 10 HN titles, choose article biased to `3D`, `MCP`, robotics, AI, disruption.                                                             | P0       |
| **FR‑3**  | Pull GitHub Trending (global) and pick top MCP repo of the day.                                                                                        | P0       |
| **FR‑4**  | Scrape Phoenix Business Journal Technology/Real‑Estate feed, pick most relevant article.                                                               | P0       |
| **FR‑5**  | Query Notion transcript DB; for records within **current week** download → transcribe (local Whisper) → store file under `/paicc-2 copy/transcripts/`. | P1       |
| **FR‑6**  | Cycle engine maintains JSON with keys `year`, `state_index`, `days_left`.                                                                              | P0       |
| **FR‑7**  | Generate Oscars, invention, president, etc., from local CSV datasets keyed by `CurrentStudyYear`.                                                      | P1       |
| **FR‑8**  | Produce TXT and update XLSX (copy of yesterday + new row).                                                                                             | P0       |
| **FR‑9**  | Send email with TXT body (inline, not attachment).                                                                                                     | P0       |
| **FR‑10** | No consecutive repetition of `CodebaseToday` unless repo list = 1.                                                                                     | P0       |
| **FR‑11** | If any field fails, insert “(data unavailable)” and continue.                                                                                          | P0       |

---

## 7 — Non‑Functional Requirements

- **Performance:** ≤ 120 s runtime.
- **Reliability:** retry external calls × 3 (exponential back‑off).
- **Security:** `.env` secrets, git‑ignored.
- **Observability:** JSON logs; alert email on exception.

---

## 8 — Data & External Services

| Service         | Endpoint                             | Daily Calls | Notes                            |
| --------------- | ------------------------------------ | ----------- | -------------------------------- |
| Hacker News     | `/v0/topstories`, `/item/<id>`       | ≤ 11        |  select best‑fit article locally |
| GitHub Trending | scrape HTML                          |  1          | throttle to 1 req/min            |
| GitHub API      | `/users/odgsully/repos`              |  1          | for CodebaseToday                |
| PBJ             | RSS feed                             |  1          | may require paywall bypass       |
| Notion          | REST API (transcripts & quiz tables) |  ≤ 10       | filtered queries                 |
| OpenAI          | `/chat/completions`                  |  \~20       | summarisation & creativity       |

---

## 9 — Persistence & File Layout

```
Jarvis_BriefMe/
└── Outputs/
    ├── dailies/
    │   └── Daily_MM.DD.YY.txt
    └── tables/
        └── Table_MM.DD.YY.xlsx
```

`Table_*.xlsx` replicates prior sheet and appends today’s row; column A = ISO date, columns B… = all placeholders in template order.

---

## 10 — Testing Strategy

- **Unit** – mock HTTP & OpenAI.
- **Cycle tests** – ensure year/state/day logic across 10 iterations.
- **Integration** – dry‑run writes files but mocks SMTP.
- **E2E smoke** – GitHub Action @ 03:00 UTC.

---

## 11 — Deployment & Ops

- **Runtime:** Python 3.12.
- **Host:** Fly.io micro‑VM with cron (`fly.toml` schedule `0 12 * * *` for 05:00 AZ, UTC−7).
- **CI/CD:** GitHub Actions → lint → test → deploy.

---

## 12 — Open Questions / Risks

1. PBJ paywall—may need 3‑rd‑party scraping API.
2. Notion rate limits with multiple DBs.
3. XLSX growth—switch to Parquet after 1 year?

---

## Appendix A — Full Email Template

*(Embed the “New Template” verbatim so dev team has single source; omitted here for brevity.)*

## Appendix B — Placeholder Mapping Table

*(Detailed field‑to‑API/prompt matrix; maintained in **`docs/placeholder_map.xlsx`**.)*

