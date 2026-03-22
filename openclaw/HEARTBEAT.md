# HEARTBEAT vs CRON — Don't Mix Them

> Heartbeat is a pulse check. Cron is a surgery. Keep them separate or everything slows down.

---

## Heartbeat — Lightweight Checks (Every 30-60 minutes)

Heartbeat runs frequently. It must be fast and non-blocking.

**Heartbeat does:**
- Read email / check inbox
- Check deploy status
- Monitor error logs
- Scan for new GitHub notifications
- Quick health checks on running services

**Heartbeat does NOT:**
- Generate content (audio, video, images)
- Run complex multi-step workflows
- Deploy or publish anything
- Process large datasets
- Call slow external APIs

**Rule:** If a heartbeat tick takes more than 2 minutes, it belongs in a cron.

---

## Cron — Complex Chains (Separate Files, Scheduled)

Crons handle heavy, multi-step workflows. Each cron lives in its own file.

**Examples:**

| Cron | Schedule | File |
|------|----------|------|
| Generate audio, overlay on image, publish to YouTube | Every 3 days | `crons/youtube-publish.md` |
| Scrape competitor pricing, update comparison page | Weekly | `crons/competitor-scan.md` |
| Full backup + integrity check | Daily | `crons/backup.md` |
| Generate weekly report, email to stakeholders | Monday 9 AM | `crons/weekly-report.md` |

**Rules:**
1. One cron per file. No mega-cron files with 10 different jobs.
2. Each cron file specifies its own schedule, dependencies, and failure handling.
3. Crons never run inside heartbeat. If heartbeat triggers a cron, it spawns it as a separate process.
4. Cron failures don't block heartbeat. Heartbeat failures don't block crons.

---

## Configuration

```bash
# Heartbeat interval (in heartbeat config or openclaw.json)
heartbeat_interval: 30m  # 30-60 minutes recommended

# Cron schedules (per cron file)
# Each cron/*.md file has its own schedule header
```

**Keep heartbeat lean. Keep crons isolated. Never mix them.**
