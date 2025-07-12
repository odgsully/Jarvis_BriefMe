# Gmail Email Setup Instructions

## Current Status
- ✅ **Automation**: Daily briefing scheduled for 5:00 AM Arizona time
- ❌ **Email**: Gmail authentication failing (needs app password)
- ✅ **Generation**: Daily briefings generate successfully

## Fix Email Authentication

### Step 1: Enable 2-Factor Authentication
1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Sign in to `gbsullivan6@gmail.com`
3. Under "Signing in to Google", click "2-Step Verification"
4. Follow the setup process to enable 2FA

### Step 2: Generate App Password
1. Go to [App Passwords](https://myaccount.google.com/apppasswords)
2. Sign in to `gbsullivan6@gmail.com`
3. Select "Mail" for the app
4. Select "Mac" for the device
5. Click "Generate"
6. Copy the 16-character app password (format: xxxx-xxxx-xxxx-xxxx)

### Step 3: Update Environment File
1. Open the `.env` file in the project directory
2. Replace the current `GMAIL_APP_PASSWORD` value:
   ```
   GMAIL_APP_PASSWORD=your-16-character-app-password-here
   ```
3. Save the file

### Step 4: Test Email
```bash
cd "/Users/garrettsullivan/Desktop/AUTOMATE/Vibe Code/Jarvis_BriefMe"
make email
```

## Automation Details

### Schedule
- **Time**: 5:00 AM Arizona time (daily)
- **Timezone**: America/Phoenix (no DST)
- **Cron**: `0 12 * * *` (12:00 PM UTC)

### What Happens Daily
1. System wakes up at 5:00 AM AZ time
2. Generates fresh content (Hacker News, GitHub, AI facts, etc.)
3. Creates Daily_MM.DD.YY.txt and Table_MM.DD.YY.xlsx files
4. Sends email to `gbsullivan@mac.com`
5. Logs activity to `logs/daily_TIMESTAMP.log`

### Files Created Daily
- **TXT**: `Outputs/dailies/Daily_MM.DD.YY.txt`
- **XLSX**: `Outputs/tables/Table_MM.DD.YY.xlsx`
- **LOG**: `logs/daily_YYYY-MM-DD_HH-MM-SS.log`

## Management Commands

### View Logs
```bash
# Check latest log
tail -f logs/daily_*.log

# View all recent logs
ls -la logs/
```

### Manual Execution
```bash
# Generate without email
make run

# Generate with email
make email

# Run the scheduled script manually
./run_daily.sh
```

### Remove Automation
```bash
# Edit crontab and delete the Jarvis line
crontab -e
```

### Check Automation Status
```bash
# View current cron jobs
crontab -l

# Check if cron service is running
sudo launchctl list | grep cron
```

## Troubleshooting

### Email Issues
- **Error 535**: Wrong app password or 2FA not enabled
- **Error 534**: Account locked or suspicious activity
- **Error 550**: Recipient address issue

### Automation Issues
- Check cron service: `ps aux | grep cron`
- Verify file permissions: `ls -la run_daily.sh`
- Check logs: `tail logs/daily_*.log`

### Testing Email Manually
```python
# Test Gmail SMTP directly
import smtplib
from email.mime.text import MIMEText

msg = MIMEText("Test email")
msg['Subject'] = "Test"
msg['From'] = "gbsullivan6@gmail.com"
msg['To'] = "gbsullivan@mac.com"

with smtplib.SMTP('smtp.gmail.com', 587) as server:
    server.starttls()
    server.login("gbsullivan6@gmail.com", "your-app-password")
    server.send_message(msg)
```

## Success Criteria
When everything is working:
1. You'll receive a daily email at ~5:00 AM AZ time
2. Log files show successful completion
3. New TXT/XLSX files appear in Outputs/
4. Email contains rich, AI-generated content