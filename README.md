# NotSteam 🎮

_An overengineered game database CLI_

Read the original README [here](README2.md).

## What is this?

Our teacher asked us to "add 20 movies to a database." We took that personally and built a cloud-hosted game database with 2300+ entries, AI-generated data, fuzzy search, and a TUI that makes you feel like a hacker from a 90s movie.

## Getting Started

```bash
# Clone the repo
git clone https://github.com/ogyeet10/NotSteam.git
cd NotSteam

# Run the magic setup script (works on Windows and MacOS!)
# In VSCode: Just click the play button on setup.py
python setup.py

# Restart VSCode (because Windows gonna Windows, might not be needed on macOS)

# Run the thing
uv run main.py
```

That's it. If this doesn't work, your computer might be haunted.

## The Stack (aka "How We Overengineered a School Assignment")

- **Python** - Surprisingly not TypeScript for once
- **Convex** - Because Python tuples are too easy
- **OpenAI API (GPT-5)** - Generated all 2300 game entries + live AI editing
- **OpenAI Responses API** - Streaming reasoning summaries for edits
- **prompt_toolkit** - text input but **fun**
- **Rich** - Beautiful terminal UI with live updates
- **UV** - Because pip is annoying

## Features That Shouldn't Exist in a School Project

### Search & Query

- **Fuzzy search with typo tolerance** - Type "apex legands" and still find Apex Legends
- **Smart disambiguation** - "cod" could mean 7 different games? We ask which one
- **Nickname support** - "botw" works just as well as "The Legend of Zelda: Breath of the Wild"
- **Natural language queries** - Ask questions like "show me roguelikes" or "what games were made by Valve"
- **Advanced filtering** - Search by year, rating, playtime, VR support, price model, and more

### AI-Powered Editing (NEW!)

- **Add games with AI** - Type a game title, AI generates complete metadata with 30+ fields
- **Live reasoning display** - Watch GPT-5 think through classifications in real-time
- **AI-powered revisions** - Request changes in natural language ("make the summary shorter", "add more tags")
- **Prompt injection protection** - Built-in roasting system that rejects vandalism attempts with legendary burns
- **Auto-validation** - AI cross-checks data against web sources when needed
- **Smart persistence** - Direct integration with Convex for seamless database updates

### Editing Workflow

- **Edit existing games** - Type "edit portal" to modify any game in the database
- **Quick edit access** - After viewing a game, just type "edit" to modify it
- **Interactive review** - Preview changes before saving with beautiful formatted displays
- **Multi-field editing** - Modify any combination of: platforms, genres, tags, release year, rating, etc.

### UI/UX

- **Beautiful TUI** - Rich panels, tables, and formatting that make your eyes happy
- **Streaming updates** - Live markdown rendering of AI reasoning as it generates
- **Interactive menus** - Arrow key navigation for choices (add/edit/discard)
- **Smart fallbacks** - Graceful degradation when advanced features aren't available
- **Helpful toolbars** - ESC to cancel, Enter to confirm, always visible

### Infrastructure

- **AI-generated database** - 2300 games with detailed metadata
- **Cloud-hosted** - Convex backend because SQL is ancient technology
- **One-click setup** - Script installs UV, sets up env, and holds your hand through everything
- **Structured schemas** - JSON schema validation ensures data consistency

## Example Queries

### Search & Discovery

```
show me games made by Valve
tell me about botw
show me battle royale games
tell me about cod
show me vr games
show me roguelikes
what games were made in 2015
games rated at least 4.5
show me free to play games
help
```

### Adding & Editing Games (NEW!)

```
add a game
> Hollow Knight

edit portal
> Make the summary more concise

edit
> Add "metroidvania" to tags

make changes to skyrim
> Update the release year to 2011
```

## How It Works

### Core Search

1. **Database**: 2300+ games stored in Convex with full-text search indexes
2. **Fuzzy Matching**: Convex's built-in search handles typos automatically
3. **Nickname System**: Has a alias mapping for common game abbreviations
4. **Disambiguation**: When multiple games match, we ask you which one
5. **TUI**: A good looking TUI with panels, tables, and formatting

### AI-Powered Editing (NEW!)

1. **GPT-5 with Reasoning**: Uses OpenAI's latest model with extended thinking capability
2. **Structured Output**: JSON schema validation ensures consistent 30+ field classifications
3. **Web Search Integration**: AI can fetch real-time data when needed (release dates, platforms, etc.)
4. **Streaming Reasoning**: Live markdown display shows AI's thought process as it works
5. **Prompt Injection Defense**: Custom moderation tool rejects vandalism with devastating roasts
6. **Revision Flow**: Multi-turn conversations let you refine classifications iteratively
7. **Citation Stripping**: Automatically removes AI-generated citations from final output
8. **Convex Integration**: Seamless updates/inserts with conflict detection

## Project Structure

```
NotSteam/
├── main.py                  # Main CLI application with natural language query system
├── game_editor.py           # AI-powered add/edit UI with GPT-5 integration
├── match.py                 # Pattern matching engine for natural language
├── convex/                  # Convex backend (schema + ingest)
│   ├── schema.ts            # Convex data model and indexes
│   ├── ingest.ts            # Upload helpers and utilities (addGame, updateGame)
│   ├── games.ts             # Game queries/mutations
│   └── _generated/          # Convex generated client/server APIs
├── gamesDB/                 # Data generation and push scripts
│   ├── api.py               # Local helpers for data handling
│   ├── push_to_convex.py    # Push JSONL batches into Convex
│   ├── game_classification_schema.json  # JSON schema for AI validation
│   ├── utils/               # Batch generation/stripping utilities
│   └── *.jsonl              # Generated game and alias batches
├── setup.py                 # One-click setup automation
├── pyproject.toml           # Python project config (uv)
├── package.json             # Node workspace (Convex tooling)
├── node_modules/            # Node dependencies for Convex tooling
├── README.md                # This file
└── README2.md               # Original/legacy README
```

## The Story Behind This Madness

**Assignment**: "Add 20 movies to the provided database and one more search function"

**What We Did**:

### The Database

- Generated 2300 game entries with AI
- Created a good looking TUI with autocomplete
- Implemented fuzzy search and disambiguation
- Wrote an automated setup script
- Added nickname support for common abbreviations

### The Editor

- Integrated GPT-5
- Built a live-streaming reasoning display (watch AI think in real-time)
- Implemented natural language editing ("make the summary shorter")
- Added prompt injection defense
- Created interactive add/edit flows with arrow key navigation
- Used web search for fact-checking during classification

## Known Issues

- Sometimes we still find games missing from the database
- AI-generated data may not be 100% accurate
- OpenAI API key required for add/edit features (search still works without it)

## Requirements

### Core Features (Search & Query)

- Python 3.10+
- Convex account (free tier works)

### AI Features (Add/Edit Games)

- OpenAI API key with GPT-5 access
- Set `OPENAI_API_KEY` environment variable
- The app will notify you if the key is missing

## Credits

**Aidan Leuenberger** (@ogyeet10) - The guy who couldn't just add 20 movies like a normal person

**Daniel Mazurok** (@dimazurok) & **Logan Magana** (@Logan-Magana) - Scaffolded the initial code for the project

Built with assistance from:

- **OpenAI API** - Generated 2300 game entries so I didn't have to
- **OpenAI GPT-5** - Generated 2300 game entries + powers the AI editor
- **uv** - Made Python dependency management feel like npm
- **My groupmates** - Provided the initial scaffolding
