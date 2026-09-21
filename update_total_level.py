#!/usr/bin/env python3
import os
import sys

import requests

WOM_API = "https://api.wiseoldman.net/v2"
DISCORD_API = "https://discord.com/api/v10"


def get_config():
    try:
        return {
            "group_id": os.environ["WOM_GROUP_ID"],
            "token": os.environ["DISCORD_BOT_TOKEN"],
            "channel_id": os.environ["DISCORD_CHANNEL_ID"],
            "user_agent": os.environ.get("WOM_USER_AGENT", "gim-discord-total-level-bot"),
            "template": os.environ.get("NAME_TEMPLATE", "📊 Total Level: {total:,}"),
        }
    except KeyError as missing:
        sys.exit(f"Missing environment variable: {missing}")


def get_group_total_level(cfg):
    resp = requests.get(
        f"{WOM_API}/groups/{cfg['group_id']}/hiscores",
        params={"metric": "overall"},
        headers={"User-Agent": cfg["user_agent"]},
        timeout=30,
    )
    resp.raise_for_status()

    total = 0
    for entry in resp.json():
        name = (entry.get("player") or {}).get("displayName", "?")
        level = (entry.get("data") or {}).get("level", -1)
        if isinstance(level, int) and level > 0:
            total += level
            print(f"  {name}: {level}")
        else:
            print(f"  {name}: no level data (skipped)")
    return total


def rename_channel(cfg, new_name, dry_run):
    headers = {"Authorization": f"Bot {cfg['token']}"}
    url = f"{DISCORD_API}/channels/{cfg['channel_id']}"

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

    print("Fetching group levels from Wise Old Man...")
    total = get_group_total_level(cfg)
    if total <= 0:
        sys.exit("Got a total of 0, so something is off (wrong group ID?). Not renaming.")

    print(f"Group total level: {total:,}")
    rename_channel(cfg, cfg["template"].format(total=total), dry_run)


if __name__ == "__main__":
    main()
