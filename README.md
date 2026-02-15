# Manga Update Discord Bot

A Python-based Discord bot that monitors official VIZ Shonen Jump chapter pages and automatically posts notifications to a Discord channel when new manga chapters are released.

Supports slash commands to dynamically track and manage series without editing the code.

---

## Features

- Automatic chapter update detection  
- Posts updates directly to a Discord channel  
- `/track` command to add new manga  
- `/untrack` command to remove manga  
- `/list` command to view tracked series  
- Persistent tracking using local JSON storage  
- Asynchronous architecture using `asyncio`

---

## Tech Stack

- Python
- discord.py
- aiohttp
- BeautifulSoup4
- python-dotenv

---

## Setup Instructions

### 1. Clone the repository

    git clone https://github.com/anglerona/manga-discord-bot.git
    cd manga-discord-bot

---

### 2. Create a virtual environment

    python -m venv .venv

Activate it:

**Windows (PowerShell)**

    .venv\Scripts\Activate.ps1

**Git Bash / macOS / Linux**

    source .venv/Scripts/activate

---

### 3. Install dependencies

    pip install -U discord.py aiohttp beautifulsoup4 python-dotenv

---

### 4. Create a `.env` file

Create a file named `.env` in the project root:

    DISCORD_TOKEN=your_bot_token_here
    CHANNEL_ID=your_channel_id_here
    GUILD_ID=your_server_id_here

Never commit your `.env` file to version control.

---

### 5. Run the bot

    python bot.py

---

## Slash Commands

| Command | Description |
|----------|-------------|
| `/track name url` | Start tracking a VIZ Shonen Jump chapters URL |
| `/untrack name` | Stop tracking a series |
| `/list` | View currently tracked series |

Example:

    /track name:One Piece url:https://www.viz.com/shonenjump/chapters/one-piece

---

## Security Notes

- `.env`, `.venv/`, and `state.json` are excluded via `.gitignore`
- Reset your bot token immediately if it is ever exposed
- Only official VIZ Shonen Jump chapter listing pages are supported

---

## Future Improvements

- Role mentions for updates  
- Multi-channel support  
- Database storage (SQLite/PostgreSQL)  
- Docker support  
- Logging and monitoring system  

