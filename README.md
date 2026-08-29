# Daily Job Watcher

Checks three Maldives job sources every day and sends you a Telegram
message when a new listing matches your profile (healthcare
operations, clinic administration, general management/operations
leadership). Runs for free on GitHub Actions — no server, no paid
plan.

**Sources checked:** job-maldives.com, jobsicle.mv, mycareer.gov.mv
(the official government portal, which is also where Tree Top
Hospital's listings tend to appear).

## One-time setup (about 10 minutes)

### 1. Create a Telegram bot
1. Open Telegram, search for **@BotFather**, and start a chat.
2. Send `/newbot` and follow the prompts (give it any name/username).
3. BotFather will reply with a **token** like `123456:ABC-def...` — copy it.

### 2. Get your chat ID
1. Search for your new bot in Telegram and send it any message (e.g. "hi").
2. In a browser, visit:
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   (replace `<YOUR_TOKEN>` with the token from step 1)
3. Look for `"chat":{"id":123456789,...}` in the response — that number
   is your chat ID.

### 3. Create the GitHub repo
1. On GitHub, create a new **private** repository (e.g. `job-watcher`).
2. Upload all the files from this folder into it (or `git push` them).

### 4. Add your secrets
1. In your new repo, go to **Settings → Secrets and variables → Actions**.
2. Click **New repository secret** and add:
   - `TELEGRAM_BOT_TOKEN` → the token from step 1
   - `TELEGRAM_CHAT_ID` → the chat ID from step 2

### 5. Turn it on
GitHub Actions is enabled by default. The workflow in
`.github/workflows/daily-check.yml` will now run automatically every
day at 05:00 UTC (~9:00 AM Maldives time).

To test it right away instead of waiting: go to the **Actions** tab in
your repo → **Daily Job Check** → **Run workflow**.

## Customizing

- **Keywords**: edit the `KEYWORDS` and `EXCLUDE_KEYWORDS` lists near
  the top of `job_watcher.py` to change what counts as a match.
- **Time**: edit the `cron` line in `.github/workflows/daily-check.yml`
  (format is `minute hour * * *`, in UTC).
- **More sources**: `RSS_FEEDS` covers Blogger-based sites (feed URL
  is `<site>/feeds/posts/default?alt=rss`). `JOBSICLE_PAGES` and
  `MYCAREER_PAGES` are plain HTML pages scraped directly — add more
  page URLs (e.g. further pagination) to check deeper into each site.

## A note on the Jobsicle/MyCareer scrapers

Unlike the RSS feed, these two work by reading the site's HTML
directly and pulling out job links — there's no official feed for
them. This is reliable as long as the sites' page structure doesn't
change, but if either site redesigns its listing page, that source
may need small script updates. If a run stops finding matches you
know exist, that's the first place to check — the RSS-based
job-maldives.com source is more resilient long-term.

## How it avoids duplicate alerts

Every link it has already sent you is stored in `seen.json`. The
workflow commits this file back to the repo after each run, so it
remembers what it already told you — even though each run starts on a
fresh machine.

## Cost

Free. GitHub Actions gives 2,000 free minutes/month on private repos
(this job takes well under a minute per run — roughly 30 minutes/month
total), and Telegram's Bot API has no usage cost.
