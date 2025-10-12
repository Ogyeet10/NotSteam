# NotSteam 🎮

_An overengineered game database CLI_

Read the original README [here](README2.md).

## What is this?

Our teacher asked us to "add 20 movies to a database." We took that personally and built a cloud-hosted game database with 2300+ entries, AI-generated data, fuzzy search, and a TUI that makes you feel like a hacker from a 90s movie.

## The Stack (aka "How We Overengineered a School Assignment")

- **Python** - Surprisingly not TypeScript for once
- **Convex** - Because Python tuples are too easy
- **OpenAI API** - Generated all 2300 game entries
- **prompt_toolkit** - text input but **fun**
- **UV** - Because pip is annoying

## Features That Shouldn't Exist in a School Project

- **Fuzzy search with typo tolerance** - Type "apex legands" and still find Apex Legends
- **Smart disambiguation** - "cod" could mean 7 different games? We ask which one
- **Nickname support** - "botw" works just as well as "The Legend of Zelda: Breath of the Wild"
- **Beautiful TUI** - Rich panels, tables, and formatting that make your eyes happy
- **AI-generated database** - 2300 games with detailed metadata
- **Cloud-hosted** - Convex backend because SQL is ancient technology
- **One-click setup** - Script installs UV, sets up env, and holds your hand through everything

## Getting Started

```bash
# Clone the repo
git clone https://github.com/ogyeet10/NotSteam.git
cd NotSteam

# Run the magic setup script (works on Windows!)
# In VSCode: Just click the play button on setup.py
python setup.py

# Restart VSCode (because Windows gonna Windows, should not be needed on macOS)

# Run the thing
uv run main.py
```

That's it. If this doesn't work, your computer might be haunted.

## Example Queries

```
show me games made by Valve
tell me about botw
show me battle royale games
tell me about cod
show me vr games
help
```

## How It Works

1. **Database**: 2300+ games stored in Convex with full-text search indexes
2. **AI Generation**: Used OpenAI to generate game metadata
3. **Fuzzy Matching**: Convex's built-in search handles typos automatically
4. **Nickname System**: Has a alias mapping for common game abbreviations
5. **Disambiguation**: When multiple games match, we ask you which one
6. **TUI**: A good looking TUI with panels, tables, and formatting

## Project Structure

```
NotSteam/
├── main.py                  # The main CLI application (TUI)
├── match.py                 # Query matching and disambiguation logic
├── convex/                  # Convex backend (schema + ingest)
│   ├── schema.ts            # Convex data model and indexes
│   ├── ingest.ts            # Upload helpers and utilities
│   ├── games.ts             # Game queries/mutations
│   ├── http.ts              # HTTP functions (if any)
│   └── _generated/          # Convex generated client/server APIs
├── gamesDB/                 # Data generation and push scripts
│   ├── api.py               # Local helpers for data handling
│   ├── push_to_convex.py    # Push JSONL batches into Convex
│   ├── utils/               # Batch generation/stripping utilities
│   └── *.jsonl              # Generated game and alias batches
├── setup.py                 # One-click setup automation
├── pyproject.toml           # Python project config (uv)
├── uv.lock                  # uv lockfile
├── package.json             # Node workspace (Convex tooling)
├── pnpm-lock.yaml           # pnpm lockfile
├── pnpm-workspace.yaml      # pnpm workspace config
├── node_modules/            # Node dependencies
├── README.md                # This file
└── README2.md               # Original/legacy README
```

## The Story Behind This Madness

**Assignment**: "Add 20 movies to the provided database and one more search function"

**What We Did**:

- Generated 2300 game entries with AI
- Built a cloud database with proper indexing
- Created a professional TUI with autocomplete
- Implemented fuzzy search and disambiguation
- Wrote an automated setup script
- Added nickname support for common abbreviations

**Why**: Because when you give a TypeScript developer UV and tell them to use Python, they will absolutely go nuclear on your assignment requirements.

## Known Issues

- Sometimes we still find games missing from the database
- The setup script makes things _too_ easy for my groupmates
- My teacher's rubric wasn't designed for projects with cloud infrastructure
- We may have set unrealistic expectations for future group projects

## Credits

**Aidan Leuenberger** (@ogyeet10) - The guy who couldn't just add 20 movies like a normal person

Built with assistance from:

- **OpenAI API** - Generated 2300 game entries so I didn't have to
- **GPT-5** - Wrote the more complex code
- **uv** - Made Python dependency feel like npm
- **My groupmates** - Provided the initial scaffolding
