# Automated-Shorts-Uploader

## Channel authorization (start here)

This repo is the machine's single home for YouTube credentials. Other projects
(ClipForge, Conductor) borrow this venv and its tokens rather than keeping their
own.

**Double-click these** — no shell required:

| File | What it does |
|---|---|
| `authorize-channel.cmd` | Authorize one channel (opens a browser) |
| `check-channels.cmd` | Which channels are authorized, and is each token alive |

From a shell, note the syntax: Windows PowerShell 5.1 has **no `&&` operator**
(it is a parser error) and needs `.\` before a relative executable, so use `;`
and the leading dot-slash:

```powershell
cd C:\Users\super\Documents\GitHub\Automated-Shorts-Uploader; .\.venv\Scripts\python.exe channel_auth.py list
```

The subcommands are `add`, `list`, `refresh`, `remove <slug>`.

> The `.cmd` files must stay **CRLF with plain ASCII**. Written with LF endings
> or a stray em-dash, `cmd` mis-parses them and emits `'m' is not recognized`
> before doing anything useful.

**One token per channel.** A YouTube token is bound to the channel chosen at
Google's consent screen; `onBehalfOfContentOwner` is for CMS partners, not for
someone with several Brand Accounts. Run `add` once per channel and pick the
right Brand Account each time — a video cannot be moved between channels
afterwards. Tokens land in `tokens/<slug>.json`, filed under the channel
`channels.list(mine=True)` reports rather than under whatever you called it.

**Why tokens kept dying.** Two independent rules; the first is what actually bit
this project.

*Testing-mode expiry (7 days).* The `automated-shorts-upload` OAuth consent
screen sat in **Testing** with External user type from creation until
2026-08-02, and in Testing every refresh token expires after a week. It hid
itself because `token_manager.refresh_token()` catches the failure and calls
`create_new_token()`, which **re-runs the browser consent flow** — so
`youtube_token.json` kept getting rewritten and looked like one long-lived
credential while really re-prompting every seven days. That silent loop was the
"why do I keep authorizing this" problem.

Resolved by **Audience → Publish app** (done 2026-08-02, status now *In
production*, still External, not submitted for verification). Only tokens minted
after publishing are long-lived, so re-authorize once.

*Idle expiry (6 months).* Separately, Google drops a refresh token unused for six
months. `refresh` prevents that — Conductor runs it weekly, and `list` warns once
a token passes 120 days.

`channel_auth.py` deliberately does **not** re-run consent on a failed refresh.
It reports `expired` and makes you run `add` on purpose, so this can never hide
again.

**At consent you will see "Google hasn't verified this app"** — click *Advanced*,
then *Go to …*. That is permanent without submitting for verification and is fine
here. The OAuth user cap of 100 distinct accounts applies over the project's
entire lifetime and cannot be reset.

The legacy single `youtube_token.json` is folded into `tokens/` automatically on
first use, so an existing one-channel setup keeps working.

---

Send email of link to video and it gets automatically uploaded to my shorts channel

This project demonstrates how to use the Gmail API to authenticate and monitor emails programmatically. It includes setting up the Gmail API, authenticating, and fetching emails from a specific sender.

## **Setup Instructions**

### **1. Prerequisites**
1. Install Python 3.x on your system.
   Install required Python libraries:
   ```bash
   pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
   
2. Google Cloud Project Setup
Create a New Project:

Go to Google Cloud Console.
Create a new project.
Enable Gmail API:

Navigate to APIs & Services > Library.
Search for "Gmail API" and enable it.
Set Up OAuth Consent Screen:

Go to APIs & Services > OAuth consent screen.
Choose "External" for the user type and fill in the required details.
Add the email address you’ll use for testing under Test Users.
Create OAuth 2.0 Credentials:

Go to APIs & Services > Credentials.
Click Create Credentials > OAuth 2.0 Client ID.
Application type: Desktop App.
Download the resulting JSON file and save it as credentials.json in the project directory.

3. Project Setup
Clone or download the repository:

bash
Copy code
git clone <repository-url>
cd <repository-directory>
Place the credentials.json file in the project directory.

Run the script to authenticate:

bash
Copy code
python AuthenticateEmail.py
During the first run:

A browser will open asking for permission to access your Gmail.
Complete the authentication process.
A token.json file will be created to store the access and refresh tokens.

4. Fetching Emails
Modify the AuthenticateEmail.py script to customize email queries:
Change the sender email address (justinferrari91@gmail.com) or add additional filters.
Run the script to continuously monitor for emails:
bash
Copy code
python AuthenticateEmail.py

6. Notes
The token.json file is reused for future authentications, so you don’t need to log in again.
Ensure the credentials.json and token.json files are stored securely and not shared publicly.
