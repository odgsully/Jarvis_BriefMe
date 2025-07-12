# Jarvis BriefMe 🤖

> **Automated Daily Intelligence Brief Generator**  
> Delivers comprehensive morning briefings at 5:00 AM Arizona time with AI-generated content, current events, and educational material.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Active](https://img.shields.io/badge/Status-Active%20%26%20Scheduled-green.svg)](https://github.com)

## 🚀 What It Does

**Jarvis BriefMe** automatically generates and delivers personalized daily briefings containing:

- 📰 **Top Hacker News** articles with AI analysis
- 🔧 **GitHub Trending** MCP repositories 
- 🌍 **Random Country** profiles with interesting facts
- 📚 **Historical Facts** (WWI, WWII, Europe, etc.)
- 🏛️ **Educational Content** (year cycles, inventions, presidents)
- 🏌️ **State-specific Info** (golf courses, geography)
- 🗣️ **Multilingual Phrases** (10 languages)
- 💻 **Codebase Reviews** from GitHub repositories
- 📊 **Excel Tables** with cumulative data tracking

## ⭐ Key Features

- **🕐 Fully Automated**: Runs daily at 5:00 AM Arizona time
- **🤖 AI-Powered**: Uses OpenAI GPT for content generation and summaries
- **📧 Email Delivery**: Sends formatted briefings via Gmail SMTP
- **📁 File Persistence**: Saves TXT and XLSX files for historical tracking
- **🔄 Cyclic Learning**: 3-day rotation system for states and historical periods
- **🛡️ Robust Error Handling**: Graceful fallbacks and comprehensive logging
- **🧪 Comprehensive Testing**: 90%+ test coverage with end-to-end validation

## 🏗️ Architecture

```
src/
├── main.py                 # Main orchestrator
├── fetchers/               # Data source integrations
│   ├── hn.py              # Hacker News API
│   ├── github_trend.py    # GitHub trending scraper  
│   ├── notion.py          # Notion database queries
│   └── countries.py       # Country information
├── generators/             # Content generators
│   ├── cycle.py           # State/year cycle engine
│   ├── summariser.py      # OpenAI GPT wrapper
│   └── codebase.py        # GitHub repository analyzer
├── template_engine.py     # Jinja2 templating
├── file_writer.py         # TXT/XLSX output handlers
├── emailer.py            # Gmail SMTP integration
└── utils/                # Utilities
    ├── logger.py         # Structured logging
    └── retry.py          # Async retry decorator
```

## 🚀 Quick Start

### 1. Installation
```bash
git clone <repository-url>
cd Jarvis_BriefMe
make install  # Creates venv and installs dependencies
```

### 2. Configuration
Copy `.env.example` to `.env` and configure:
```bash
OPENAI_API_KEY=your-openai-api-key
GMAIL_FROM=your-email@gmail.com
GMAIL_TO=recipient@email.com
GMAIL_APP_PASSWORD=your-gmail-app-password
NOTION_API_KEY=your-notion-integration-key
TIMEZONE=America/Phoenix
```

### 3. Usage
```bash
# Generate briefing (no email)
make run

# Generate and send email
make email

# Run tests
make test

# Check code quality
ruff check .
```

## ⏰ Automation Setup

**✅ Currently Active**: The system is already scheduled to run daily at 5:00 AM Arizona time via cron.

### View Current Schedule
```bash
crontab -l  # Shows: 0 12 * * * /path/to/run_daily.sh
```

### Manual Scheduling (if needed)
```bash
# Set up automation
./setup_scheduler.sh  # (if not already done)

# Remove automation  
crontab -e  # Delete the Jarvis line
```

## 📧 Email Setup

### Current Status
- ❌ **Email Authentication**: Needs Gmail App Password
- ✅ **Email Template**: Configured and ready
- ✅ **Scheduling**: Active automation

### Fix Email (Required Steps)
1. **Enable 2FA** on your Gmail account
2. **Generate App Password**: https://myaccount.google.com/apppasswords
3. **Update .env**: Replace `GMAIL_APP_PASSWORD` with new 16-character code
4. **Test**: Run `make email`

📋 See `EMAIL_SETUP.md` for detailed instructions.

## 📊 Output Files

### Daily Generation
- **📄 TXT Files**: `Outputs/dailies/Daily_MM.DD.YY.txt`
- **📊 XLSX Tables**: `Outputs/tables/Table_MM.DD.YY.xlsx`
- **📝 Logs**: `logs/daily_YYYY-MM-DD_HH-MM-SS.log`

### Sample Output Structure
```
Good morning sir!
Here is your daily update for Thursday, July 10, 2025.

Blogs:
For YC today, we highlight [AI Article Analysis]...

[GitHub Trending MCP Repository]...

Country of the Day: Panama 🇵🇦
[Historical Facts, Golf Courses, Educational Content]...

Project Global Citizen time!
[Multilingual phrases in 10 languages]...
```

## 🔧 Data Sources

- **📰 Hacker News**: Top articles matching keywords ["AI", "startup", "robotics", etc.]
- **🐙 GitHub**: Trending Model Context Protocol repositories
- **🌍 Countries**: 195 countries with capitals and facts
- **🎬 Historical Data**: Oscars, Presidents, Inventions (1980+)
- **📚 Notion**: Transcripts, CS terms, Spanish phrases (when configured)
- **🤖 OpenAI**: AI-generated summaries and educational facts

## 🧪 Testing

```bash
# Run full test suite
make test

# Specific test files
pytest tests/test_cycle.py      # 3-day cycle logic
pytest tests/test_e2e.py        # End-to-end integration
pytest tests/test_fetchers.py   # Data source tests
```

**Test Coverage**: 90%+ required for all commits

## 📈 Monitoring

### Check System Status
```bash
# View recent logs
tail -f logs/daily_*.log

# Check cron job
crontab -l | grep Jarvis

# Manual test run
./run_daily.sh
```

### Success Indicators
- ✅ Daily email received at ~5:00 AM AZ
- ✅ New files in `Outputs/` directories
- ✅ Log files show "Daily briefing completed successfully"
- ✅ Rich AI-generated content in briefings

## 🛠️ Development

### Project Structure
- **Modular Design**: Easily extensible data fetchers and generators
- **Async Architecture**: All I/O operations use async/await
- **Error Resilience**: Graceful degradation when data sources fail
- **Configuration-Driven**: Environment variables for all settings

### Adding New Data Sources
1. Create fetcher in `src/fetchers/`
2. Add context variables to `main.py`
3. Update template in `templates/daily_template.txt`
4. Add tests in `tests/`

## 📋 Commands Reference

| Command | Description |
|---------|-------------|
| `make install` | Set up environment and dependencies |
| `make run` | Generate briefing files only |
| `make email` | Generate briefing and send email |
| `make test` | Run test suite with coverage |
| `ruff check .` | Code linting and formatting |

## 🔍 Troubleshooting

### Common Issues
- **Email fails**: Check Gmail app password and 2FA setup
- **Notion errors**: Verify API key has `secret_` prefix
- **Missing content**: Check OpenAI API key and quota
- **Automation not running**: Verify cron service and file permissions

### Debug Mode
```bash
# Run with verbose logging
python -m src.main --email --verbose

# Check specific component
python -c "from src.fetchers.hn import HackerNewsFetcher; print('HN OK')"
```

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

## 👥 Contributors

- **@odgsully** - Product Owner & Vision
- **Claude Code** - Implementation & Architecture

---

**🤖 Jarvis BriefMe** - Your daily intelligence, delivered with precision.

*Last Updated: July 2025*