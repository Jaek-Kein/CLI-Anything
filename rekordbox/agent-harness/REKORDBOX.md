# cli-anything-rekordbox

Agent-native command-line interface for **Pioneer Rekordbox 6/7**.
Modified for the Jaek-Kein fork, 2026-10-22: expanded metadata export, native My Tag
creation/linking, comment editing, preview-first batch updates, backups and undo manifests.
See [LIBRARY_KO.md](LIBRARY_KO.md) for the current library workflow.

## What it does

Pioneer ships **no public REST/RPC API for playback control**. Rekordbox's only programmatic surfaces are:
1. **`master.db`** — SQLCipher-encrypted SQLite library
2. **Virtual MIDI** — accepts MIDI from any registered controller mapping
3. **Pro DJ Link** — read-only network broadcasts for hardware CDJs

This harness combines (1) + (2) into a single CLI:
- **Library:** direct SQLCipher writes via `pyrekordbox` (auto-extracts the static rekordbox 6/7 master key)
- **Playback:** virtual MIDI sender mapped via a bundled `Bunker.midi.csv` controller mapping
- **Output:** JSON for agent consumption (`--json`) or human-readable

## Installation

```bash
pip install -e .  # from rekordbox/agent-harness; no CLI Hub required
# Optional live MIDI dependencies:
pip install -e '.[midi]'
# Optional Windows extras for live-deck UI automation:
pip install cli-anything-rekordbox[windows]
```

**Prerequisites:**
- Python 3.11+
- Rekordbox 6 or 7 installed (master.db must be locatable)
- A virtual MIDI driver if you want live-deck control:
  - **Windows:** [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html), LoopBe, or teVirtualMIDI
  - **macOS:** IAC Driver (built-in via Audio MIDI Setup)
  - **Linux:** ALSA virtual MIDI (`snd-virmidi`)

## Quick start

```bash
# Library inspection (no MIDI needed)
cli-anything-rekordbox library count
cli-anything-rekordbox library search "Daft Punk"

# Create + populate a playlist. Writes back up master.db first and refuse to run
# while Rekordbox is open unless --force is supplied.
cli-anything-rekordbox playlist create "MyMix"
cli-anything-rekordbox playlist add "MyMix" --track-title "Track A"
cli-anything-rekordbox playlist add "MyMix" --track-title "Track B"

# Live-deck mixing (requires virtual MIDI port + mapping in rekordbox)
cli-anything-rekordbox install-mapping            # one-time: drops Bunker.midi.csv into rekordbox MidiMappings/
cli-anything-rekordbox deck play --deck 1 --port "LoopBe"
cli-anything-rekordbox deck crossfade 1 2 --secs 16

# Look up tracks and print manual load / crossfade instructions (does not mix automatically)
cli-anything-rekordbox mix "Track A" "Track B" --secs 16

# REPL mode
cli-anything-rekordbox
```

## Command groups

### `library`
| Command | Description |
|---------|-------------|
| `count` | Total tracks in library |
| `search QUERY` | Find tracks by title/artist (substring) |
| `info TRACK_ID` | Show full metadata for a track |
| `dump --out tracks.json` | Export full library as JSON |
| `update TRACK_ID [--append-comment TEXT] [--add-tag CATEGORY_ID NAME] [--apply]` | Preview/apply comment and native My Tag changes |
| `apply FILE.json [--apply]` | Preview/apply a full batch atomically, or an undo manifest |

`tag list` lists native My Tag category IDs and labels. Library exports include
album, actual key, BPM, duration in seconds/milliseconds, comments, My Tag, rating,
release year and file path. `--db PATH` selects a specific database or test snapshot.
New metadata commands always require backup and a closed Rekordbox for `--apply`.

### `playlist`
| Command | Description |
|---------|-------------|
| `list` | Show all playlists |
| `create NAME [--force] [--no-backup]` | Create new playlist |
| `add NAME --track-title T [--force] [--no-backup]` | Add track by title |
| `clear NAME [--force] [--no-backup]` | Empty a playlist |

Playlist writes create timestamped backups under `master.db`'s sibling
`cli-anything-backups/` directory before mutation. If Rekordbox is running, the
CLI refuses to write by default; `--force` acknowledges that risk but still
requires a backup. `--no-backup` is only accepted when Rekordbox is closed.

### `deck` (live MIDI)
| Command | Description |
|---------|-------------|
| `play --deck N` | Toggle play/pause |
| `sync --deck N` | Tempo sync |
| `crossfade FROM TO --secs S` | Smooth crossfade between decks |
| `eq --deck N --hi V --mid V --lo V` | EQ control (0..1) |
| `hot-cue --deck N --slot S` | Trigger hot cue 1-8 |

### High-level
| Command | Description |
|---------|-------------|
| `mix A B --secs S` | Look up two tracks and print manual loading/crossfade instructions |
| `install-mapping` | Copy Bunker.midi.csv into rekordbox's MidiMappings dir |
| `status` | Report rekordbox running state, DB path, MIDI ports |

## Architecture

```
+-----------------------------+
|  cli-anything-rekordbox     |
+-----------------------------+
            |
   +--------+----------+
   |                   |
   v                   v
+-----------+   +---------------+
| pyrekord- |   | mido +        |
| box       |   | virtual MIDI  |
+-----------+   +---------------+
   |                   |
   v                   v
+----------+    +-----------------+
| master.db|    | Rekordbox 6/7   |
| SQLCipher|    | (live decks)    |
+----------+    +-----------------+
```

## Data files

- `cli_anything/rekordbox/data/Bunker.midi.csv` — MIDI mapping (transport, mixer, EQ, hot cues, beat loops, browser nav). Pioneer-format, drops directly into rekordbox's `MidiMappings/` folder.

## JSON output

Every command supports `--json` for agent consumption:
```bash
$ cli-anything-rekordbox --json library search "Daft Punk"
[{"id": 12345, "title": "One More Time", "artist": "Daft Punk", "bpm": 123.0}, ...]
```

## Notes & caveats

- **SQLCipher access** is handled by pyrekordbox 0.5.x.
- **Library writes** require Rekordbox to be closed by default. Forced writes with `--force` are explicit, backed up first, and should be reserved for recovery/test workflows.
- **Live-deck control** depends on the user mapping the virtual MIDI port in rekordbox `Preferences → Controller → MIDI` (one-time UI step). The harness ships `Bunker.midi.csv` and an `install-mapping` command to drop it into the right folder.
- **Pioneer offers no playback REST API.** This is the closest thing.

## License
MIT — same as parent CLI-Anything project.

The above is an upstream notice preserved as-is. The repository-root LICENSE is
Apache-2.0; upstream issue #475 / PR #498 track this inconsistency.
