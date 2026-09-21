#!/usr/bin/env python3
import os
import sys
import requests

DISCORD_API = "https://discord.com/api/v10"
HISCORES_URL = "https://secure.runescape.com/m=hiscore_oldschool/index_lite.ws"


def get_config():
    try:
        return {
            "token": os.environ["DISCORD_BOT_TOKEN"],
            "channel_id": os.environ["DISCORD_CHANNEL_ID"],
            "xp_channel_id": os.environ["DISCORD_XP_CHANNEL_ID"],
            "usernames": [u.strip() for u in os.environ["PLAYER_NAMES"].split(",")],
            "template": os.environ.get("NAME_TEMPLATE", "📊┃Total Level: {total:,}"),
            "xp_template": os.environ.get("XP_TEMPLATE", "📊┃Total XP: {xp:,}"),
        }
    except KeyError as missing:
        sys.exit(f"Missing environment variable: {missing}")


def get_player_stats(username):
    resp = requests.get(
        HISCORES_URL,
        params={"player": username},
        headers={"User-Agent": "gim-discord-bot"},
        timeout=10,
    )
    if resp.status_code == 404:
        print(f"  {username}: not found on hiscores (skipped)")
        return 0, 0
    resp.raise_for_status()
    first_line = resp.text.splitlines()[0]
    parts = first_line.split(",")
    level = int(parts[1])
    xp = int(parts[2])
    print(f"  {username}: level {level}, xp {xp:,}")
    return level, xp


def get_group_stats(cfg):
    total_level = 0
    total_xp = 0
    for username in cfg["usernames"]:
        level, xp = get_player_stats(username)
        total_level += level
        total_xp += xp
    return total_level, total_xp


def rename_channel(cfg, channel_id, new_name, dry_run=False):
    headers = {"Authorization": f"Bot {cfg['token']}"}
    url = f"{DISCORD_API}/channels/{channel_id}"

    current = requests.get(url, headers=headers, timeout=30)
    current.raise_for_status()
    if current.json().get("name") == new_name:
        print("Channel name already up to date, nothing to do.")
        return

    if dry_run:
        print(f"[dry run] Would rename channel to: {new_name}")
        return

    resp = requests.patch(url, headers=headers, json={"name": new_name}, timeout=30)
    if resp.status_code == 429:
        retry = resp.json().get("retry_after", "?")
        sys.exit(f"Rate limited by Discord, try again in {retry} seconds.")
    resp.raise_for_status()
    print(f"Renamed channel to: {new_name}")


def main():
    dry_run = "--dry-run" in sys.argv
    cfg = get_config()

    print("Fetching levels from OSRS hiscores...")
    total_level, total_xp = get_group_stats(cfg)

    if total_level <= 0:
        sys.exit("Got a total of 0, something is off. Not renaming.")

    print(f"Group total level: {total_level:,}")
    print(f"Group total XP: {total_xp:,}")

    rename_channel(cfg, cfg["channel_id"], cfg["template"].format(total=total_level), dry_run)
    rename_channel(cfg, cfg["xp_channel_id"], cfg["xp_template"].format(xp=total_xp), dry_run)


if __name__ == "__main__":
    main()
