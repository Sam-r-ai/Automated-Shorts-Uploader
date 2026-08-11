r"""Per-channel YouTube authorization.

Double-click `authorize-channel.cmd` (add) or `check-channels.cmd` (list).

From a shell, mind the syntax — Windows PowerShell 5.1 has no `&&` operator and
needs `.\` before a relative executable:

    .\.venv\Scripts\python.exe channel_auth.py add       # authorize one channel
    .\.venv\Scripts\python.exe channel_auth.py list      # channels + token health
    .\.venv\Scripts\python.exe channel_auth.py refresh   # keep every token warm
    .\.venv\Scripts\python.exe channel_auth.py remove <slug>

Why one token per channel
-------------------------
A YouTube OAuth token is bound to the channel you pick at Google's consent
screen. There is no way to switch channels with one token — `onBehalfOfContentOwner`
is for CMS partners, not for someone with several Brand Accounts. So uploading
to three channels means running `add` three times and choosing a different
channel each time.

The label is never trusted. After consent this calls `channels.list(mine=True)`
and files the token under the channel Google actually granted, so a token can't
end up pointing at a channel you didn't mean.

Why tokens die, and how to stop it
----------------------------------
Two separate rules, and the first one is what bit this project:

1. **Testing-mode expiry (7 days).** While the Google Cloud OAuth consent screen
   is in "Testing" with External user type, every refresh token dies after a
   week. The `automated-shorts-upload` project was in Testing from creation
   until 2026-08-02, so every token it ever issued had a 7-day life.

   This hid itself well. `token_manager.refresh_token()` catches a failed
   refresh and calls `create_new_token()`, which re-runs the browser consent
   flow — so the token file kept getting rewritten and *looked* like one
   long-lived credential, while in reality the user was being re-prompted every
   week. That silent re-auth loop was the actual "why do I keep having to
   authorize this" problem.

   Fixed by publishing the app (Audience -> Publish app). Only tokens minted
   after that are long-lived; anything issued during Testing keeps its 7-day
   clock, so re-authorize once after publishing.

2. **Idle expiry (6 months).** Independently, Google drops a refresh token that
   has gone six months without use. `refresh` guards against that — run it on
   any cadence under six months and the clock never runs out. Conductor calls it
   weekly.

This module deliberately does NOT re-run the consent flow on a failed refresh.
`health()` reports `expired` and the caller has to run `add` on purpose, so a
recurring auth problem is visible instead of silently re-prompting.

After publishing, consent shows a "Google hasn't verified this app" screen —
click Advanced, then "Go to <app>". That is permanent without submitting for
verification, and harmless for a personal tool. Note the OAuth user cap of 100
distinct accounts applies over the project's whole lifetime and cannot be reset.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

REPO = Path(__file__).resolve().parent
TOKEN_DIR = REPO / "tokens"
CREDENTIALS = REPO / "credentials.json"
LEGACY_TOKEN = REPO / "youtube_token.json"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]

# Google drops a refresh token after 6 months unused. Warn well before that.
STALE_AFTER_DAYS = 120


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "channel"


def token_path(slug: str) -> Path:
    return TOKEN_DIR / f"{slug}.json"


def _identify(creds: Credentials) -> dict:
    """Which channel did we actually just get? Ask, never assume."""
    yt = build("youtube", "v3", credentials=creds)
    items = yt.channels().list(part="snippet,statistics", mine=True).execute().get("items", [])
    if not items:
        raise RuntimeError(
            "That account granted access but owns no YouTube channel. Pick the "
            "Brand Account for the channel you want at the consent screen."
        )
    c = items[0]
    return {
        "channel_id": c["id"],
        "title": c["snippet"]["title"],
        "custom_url": c["snippet"].get("customUrl", ""),
        "videos": int(c.get("statistics", {}).get("videoCount", 0) or 0),
        "subscribers": c.get("statistics", {}).get("subscriberCount", ""),
    }


def _write(slug: str, creds: Credentials, info: dict) -> Path:
    TOKEN_DIR.mkdir(exist_ok=True)
    p = token_path(slug)
    data = json.loads(creds.to_json())
    # The channel this token is for, carried alongside the credentials so
    # nothing downstream has to guess or hit the API to find out.
    data["_channel"] = {**info, "slug": slug, "authorized_at": _now_iso()}
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return p


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load(slug: str) -> tuple[Credentials, dict]:
    p = token_path(slug)
    if not p.exists():
        raise FileNotFoundError(f"no token for {slug!r} — double-click authorize-channel.cmd")
    raw = json.loads(p.read_text(encoding="utf-8"))
    return Credentials.from_authorized_user_info(raw, SCOPES), raw.get("_channel", {})


def health(slug: str) -> dict:
    """Is this token usable right now? Refreshes if it can, reports honestly."""
    try:
        creds, meta = load(slug)
    except Exception as e:
        return {"slug": slug, "ok": False, "state": "missing", "detail": str(e)}

    out = {"slug": slug, "ok": False, "state": "unknown", **meta}
    if creds.valid:
        out.update(ok=True, state="valid")
    elif creds.refresh_token:
        try:
            creds.refresh(Request())
            _write(slug, creds, meta)
            out.update(ok=True, state="refreshed")
        except Exception as e:
            out.update(ok=False, state="expired", detail=f"{type(e).__name__}: {e}"[:200])
    else:
        out.update(state="no refresh token")

    authorized = meta.get("authorized_at")
    if out["ok"] and authorized:
        try:
            age = datetime.now(timezone.utc) - datetime.fromisoformat(authorized)
            out["age_days"] = age.days
            # Google's 6-month unused rule is the thing that killed the old
            # token. Anything approaching that should be visible before it bites.
            out["stale"] = age.days >= STALE_AFTER_DAYS
        except ValueError:
            pass
    return out


def cmd_add(args) -> int:
    if not CREDENTIALS.exists():
        print(f"missing {CREDENTIALS} — download the OAuth client (Desktop app) "
              "from Google Cloud Console first")
        return 1

    have = sorted(p.stem for p in TOKEN_DIR.glob("*.json")) if TOKEN_DIR.is_dir() else []
    if have:
        print(f"Already authorized: {', '.join(have)}")
    print("A browser will open. Two things matter on that screen:")
    print("  1. Pick the Google account that owns the channel you want.")
    if args.account:
        print(f"     (suggesting {args.account} — confirm it is really that one)")
    elif have:
        print("     Your browser is probably still signed in as the LAST account you")
        print("     used, so choose deliberately — 'Use another account' if needed.")
    print("  2. If it offers a channel or Brand Account list, pick the RIGHT one —")
    print("     that choice is what binds this token, and it cannot be changed later.\n")

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS), SCOPES)
    # offline + consent guarantees a refresh token comes back. Without the
    # explicit prompt, re-authorizing an already-granted app returns an access
    # token only, and the result looks fine until it expires an hour later.
    #
    # select_account forces the account chooser every time. Without it Google
    # silently reuses whichever account the browser is already signed in as —
    # which, when authorizing a SECOND channel, quietly re-authorizes the first
    # one instead. That failure is invisible until you read the channel name.
    extra = {"login_hint": args.account} if args.account else {}
    creds = flow.run_local_server(
        port=0, access_type="offline", prompt="select_account consent", **extra
    )

    info = _identify(creds)

    # The most likely mistake when adding a SECOND channel is authorizing the
    # first one again, because the browser was still signed in as that account.
    # It is silent otherwise — you just get a second token for a channel you
    # already had.
    for existing in (TOKEN_DIR.glob("*.json") if TOKEN_DIR.is_dir() else []):
        try:
            meta = json.loads(existing.read_text(encoding="utf-8")).get("_channel", {})
        except (json.JSONDecodeError, OSError):
            continue
        if meta.get("channel_id") == info["channel_id"] and existing.stem != (args.name or ""):
            print(f"\n  NOTE: this is the same channel you already have as "
                  f"'{existing.stem}' ({meta.get('title')}).")
            print("  If you meant a different channel, sign out of that Google account")
            print("  (or choose 'Use another account') and run this again.\n")
            break

    slug = args.name or slugify(info["title"])
    p = _write(slug, creds, info)

    print(f"\nAuthorized: {info['title']}")
    print(f"  channel id : {info['channel_id']}")
    print(f"  handle     : {info['custom_url'] or '-'}")
    print(f"  videos     : {info['videos']}")
    print(f"  saved as   : {p.name}  (use --name to choose a different slug)")
    if not creds.refresh_token:
        print("\nWARNING: no refresh token came back — this will stop working in an hour.")
        return 1
    return 0


def cmd_list(args) -> int:
    _migrate_legacy()
    slugs = sorted(p.stem for p in TOKEN_DIR.glob("*.json")) if TOKEN_DIR.is_dir() else []
    if not slugs:
        print("no channels authorized yet — double-click authorize-channel.cmd")
        return 0

    rows = [health(s) for s in slugs]
    width = max(len(r["slug"]) for r in rows)
    for r in rows:
        mark = "ok " if r["ok"] else "DEAD"
        extra = ""
        if r.get("stale"):
            extra = f"  (unused {r['age_days']}d — refresh it, 180d kills it)"
        elif not r["ok"]:
            extra = f"  {r.get('detail', r['state'])[:80]}"
        print(f"  [{mark}] {r['slug']:<{width}}  {r.get('title', '?')}"
              f"  {r.get('custom_url', '')}{extra}")
    print(f"\n{sum(1 for r in rows if r['ok'])}/{len(rows)} usable")
    return 0 if all(r["ok"] for r in rows) else 1


def cmd_refresh(args) -> int:
    _migrate_legacy()
    slugs = sorted(p.stem for p in TOKEN_DIR.glob("*.json")) if TOKEN_DIR.is_dir() else []
    bad = []
    for s in slugs:
        r = health(s)
        print(f"  {s}: {r['state']}")
        if not r["ok"]:
            bad.append(s)
    if bad:
        print(f"\nneeds re-authorizing: {', '.join(bad)}")
        print("  double-click authorize-channel.cmd")
    return 1 if bad else 0


def cmd_rename(args) -> int:
    """Change the slug a channel is filed under.

    The default slug comes from the channel TITLE, which is often not what you
    call it — "Justin Gim Ho Cheung" for a channel everyone knows as @freegimho.
    The slug is what appears in Conductor's channel dropdown, so it should match
    your head, not YouTube's.
    """
    src = token_path(args.old)
    if not src.exists():
        print(f"no token for {args.old!r}")
        return 1
    new = slugify(args.new)
    dst = token_path(new)
    if dst.exists():
        print(f"{new!r} already exists — pick another name")
        return 1

    data = json.loads(src.read_text(encoding="utf-8"))
    data.setdefault("_channel", {})["slug"] = new
    dst.write_text(json.dumps(data, indent=2), encoding="utf-8")
    src.unlink()
    print(f"{args.old} -> {new}  ({data['_channel'].get('title')})")
    print("  Update any recipe that referenced the old name.")
    return 0


def cmd_remove(args) -> int:
    p = token_path(args.name)
    if not p.exists():
        print(f"no token file for {args.name!r}")
        return 1
    p.unlink()
    print(f"removed {p.name} (access is still granted in your Google account; "
          "revoke it at myaccount.google.com/permissions if you want it gone)")
    return 0


def _migrate_legacy() -> None:
    """Fold the original single youtube_token.json into the per-channel store,
    so an existing setup keeps working without re-authorizing."""
    if not LEGACY_TOKEN.exists() or (TOKEN_DIR.is_dir() and any(TOKEN_DIR.glob("*.json"))):
        return
    try:
        raw = json.loads(LEGACY_TOKEN.read_text(encoding="utf-8"))
        creds = Credentials.from_authorized_user_info(raw, SCOPES)
        if not creds.valid and creds.refresh_token:
            creds.refresh(Request())
        info = _identify(creds)
        _write(slugify(info["title"]), creds, info)
        print(f"[migrate] youtube_token.json -> tokens/{slugify(info['title'])}.json "
              f"({info['title']})")
    except Exception as e:
        # The legacy token is dead (this is expected — it aged out). Say so once
        # and move on; `add` is the fix.
        print(f"[migrate] the old youtube_token.json is no longer usable ({type(e).__name__}) "
              "— run `add` to authorize a channel")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="authorize a channel (opens a browser)")
    a.add_argument("--name", help="slug to store it under (default: from the channel title)")
    a.add_argument("--account", metavar="EMAIL",
                   help="which Google account to suggest at the chooser, e.g. "
                        "you@gmail.com. The chooser always appears either way; "
                        "this just pre-selects, so still read the result.")
    a.set_defaults(fn=cmd_add)

    sub.add_parser("list", help="channels and token health").set_defaults(fn=cmd_list)
    sub.add_parser("refresh", help="keep every token warm").set_defaults(fn=cmd_refresh)

    n = sub.add_parser("rename", help="file a channel under a different slug")
    n.add_argument("old")
    n.add_argument("new")
    n.set_defaults(fn=cmd_rename)

    r = sub.add_parser("remove", help="delete a stored token")
    r.add_argument("name")
    r.set_defaults(fn=cmd_remove)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
