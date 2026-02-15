import os
import re
import json
import asyncio
from typing import Optional, Tuple, Dict

import aiohttp
import discord
from bs4 import BeautifulSoup
from discord.ext import tasks
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID = int(os.environ["CHANNEL_ID"])
GUILD_ID = int(os.environ.get("GUILD_ID", "0"))

STATE_FILE = "state.json"

# matches something like: "January 18, 2026 Ch. 1171 FREE"
TOP_CHAPTER_RE = re.compile(
    r"([A-Z][a-z]+ \d{1,2}, \d{4})\s+Ch\.\s*([0-9]+(?:\.[0-9]+)?)",
    re.MULTILINE
)

def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def get_tracked(state: dict) -> Dict[str, str]:
    """
    Returns dict of {name: url}
    """
    return state.get("tracked", {})

def set_tracked(state: dict, tracked: Dict[str, str]) -> None:
    state["tracked"] = tracked

async def fetch_html(session: aiohttp.ClientSession, url: str) -> str:
    headers = {"User-Agent": "manga-notifier-discord-bot/1.0 (personal project)"}
    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as r:
        r.raise_for_status()
        return await r.text()

def parse_latest_chapter(html: str) -> Optional[Tuple[str, str]]:
    """
    Returns (date_str, chapter_str) for the first chapter entry found on the page.
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n")
    m = TOP_CHAPTER_RE.search(text)
    if not m:
        return None
    return m.group(1).strip(), m.group(2).strip()

def normalize_name(name: str) -> str:
    return name.strip().lower().replace(" ", "_")

def looks_like_viz_chapters_url(url: str) -> bool:
    return url.startswith("https://www.viz.com/shonenjump/chapters/")

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

@client.event
async def on_ready():
    print(f"Logged in as {client.user} (id={client.user.id})")

    # sync commands
    try:
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            tree.copy_global_to(guild=guild)
            await tree.sync(guild=guild)
            print(f"Slash commands synced to guild {GUILD_ID}")
        else:
            await tree.sync()
            print("Slash commands synced globally (may take time to appear).")
    except Exception as e:
        print(f"[WARN] Command sync issue: {e}")

    poll_updates.start()

@tasks.loop(minutes=30)
async def poll_updates():
    state = load_state()
    tracked = get_tracked(state)

    if not tracked:
        print("[OK] No tracked series. Use /track to add some.")
        return

    channel = client.get_channel(CHANNEL_ID)
    if channel is None:
        print("[ERROR] Could not find channel. Check CHANNEL_ID and bot permissions.")
        return

    async with aiohttp.ClientSession() as session:
        for name, url in tracked.items():
            try:
                html = await fetch_html(session, url)
                latest = parse_latest_chapter(html)
                if latest is None:
                    print(f"[WARN] Could not parse latest chapter for {name}")
                    continue

                latest_date, latest_ch = latest
                state_key = f"latest:{name}"

                if state_key not in state:
                    state[state_key] = {"date": latest_date, "ch": latest_ch, "url": url}
                    save_state(state)
                    print(f"[INIT] {name}: Ch. {latest_ch} ({latest_date})")
                    continue

                prev = state[state_key]
                if prev.get("ch") != latest_ch or prev.get("date") != latest_date:
                    await channel.send(
                        f"📣 **New chapter detected!**\n"
                        f"Series: **{name.replace('_',' ').title()}**\n"
                        f"New: **Ch. {latest_ch}** ({latest_date})\n"
                        f"{url}"
                    )
                    state[state_key] = {"date": latest_date, "ch": latest_ch, "url": url}
                    save_state(state)
                    print(f"[NOTIFIED] {name}: Ch. {latest_ch} ({latest_date})")
                else:
                    print(f"[OK] {name}: no change (still Ch. {latest_ch})")

            except Exception as e:
                print(f"[ERROR] {name}: {e}")

@poll_updates.before_loop
async def before_poll():
    await client.wait_until_ready()
    await asyncio.sleep(2)


# slash commands

@tree.command(name="track", description="Track a manga using a VIZ Shonen Jump chapters URL.")
async def track(interaction: discord.Interaction, name: str, url: str):
    name_norm = normalize_name(name)

    if not looks_like_viz_chapters_url(url):
        await interaction.response.send_message(
            "That URL doesn't look like a VIZ Shonen Jump *chapters* page.\n"
            "Example: https://www.viz.com/shonenjump/chapters/one-piece",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)
    try:
        async with aiohttp.ClientSession() as session:
            html = await fetch_html(session, url)
            latest = parse_latest_chapter(html)
            if latest is None:
                await interaction.followup.send(
                    "I could fetch the page, but I couldn't find a chapter entry to parse. "
                    "Double-check the URL is a VIZ chapters listing.",
                    ephemeral=True
                )
                return
    except Exception as e:
        await interaction.followup.send(f"Couldn't fetch that URL: `{e}`", ephemeral=True)
        return

    state = load_state()
    tracked = get_tracked(state)
    tracked[name_norm] = url
    set_tracked(state, tracked)

    latest_date, latest_ch = latest
    state[f"latest:{name_norm}"] = {"date": latest_date, "ch": latest_ch, "url": url}
    save_state(state)

    await interaction.followup.send(
        f"Tracking **{name_norm}**\n"
        f"Baseline set to **Ch. {latest_ch}** ({latest_date}).\n"
        f"I'll post updates in <#{CHANNEL_ID}>.",
        ephemeral=True
    )

@tree.command(name="untrack", description="Stop tracking a manga.")
async def untrack(interaction: discord.Interaction, name: str):
    name_norm = normalize_name(name)
    state = load_state()
    tracked = get_tracked(state)

    if name_norm not in tracked:
        await interaction.response.send_message(
            f"Not tracking **{name_norm}**. Use `/list` to see tracked series.",
            ephemeral=True
        )
        return

    tracked.pop(name_norm, None)
    set_tracked(state, tracked)
    state.pop(f"latest:{name_norm}", None)
    save_state(state)

    await interaction.response.send_message(f"Untracked **{name_norm}**.", ephemeral=True)

@tree.command(name="list", description="List tracked manga.")
async def list_tracked(interaction: discord.Interaction):
    state = load_state()
    tracked = get_tracked(state)

    if not tracked:
        await interaction.response.send_message("No tracked series yet. Use `/track`.", ephemeral=True)
        return

    lines = []
    for name, url in tracked.items():
        latest = state.get(f"latest:{name}", {})
        ch = latest.get("ch", "—")
        date = latest.get("date", "—")
        lines.append(f"• **{name}** — Ch. {ch} ({date})\n  {url}")

    await interaction.response.send_message("\n".join(lines), ephemeral=True)

client.run(DISCORD_TOKEN)
