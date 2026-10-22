---
name: "cli-anything-rekordbox"
description: >-
  Local CLI for Pioneer Rekordbox 6/7: full metadata export, native My Tag and comment updates, preview-first batch plans with backup and undo, playlists, and optional MIDI control. Library commands need no CLI Hub or MIDI driver.
---

# cli-anything-rekordbox

Agent-native CLI for Pioneer Rekordbox 6/7. Drives the DJ library and live decks programmatically.

## Installation

```bash
pip install -e .  # from the standalone repository root on RecordboxCLI
# Only for live MIDI control:
pip install -e '.[midi]'
```

**Prerequisites:**
- Python 3.11+
- Rekordbox 6 or 7 installed (`master.db` must exist)
- Virtual MIDI driver for live-deck control:
  - Windows: loopMIDI / LoopBe / teVirtualMIDI
  - macOS: IAC Driver
  - Linux: ALSA virtual MIDI (`snd-virmidi`)

## Usage

```bash
# Status check
cli-anything-rekordbox status

# REPL mode
cli-anything-rekordbox

# JSON output for agents
cli-anything-rekordbox --json library search "Daft Punk"
```

## Command Groups

### Library
| Command | Description |
|---------|-------------|
| `count` | Total track count |
| `search QUERY` | Find tracks by title/artist substring |
| `info TRACK_ID` | Full track metadata |
| `dump --out FILE.json` | Export full library as JSON |
| `update TRACK_ID [--append-comment TEXT] [--add-tag CATEGORY_ID NAME] [--apply]` | Preview/apply one track's metadata |
| `apply FILE.json [--apply]` | Preview/apply a batch or an undo manifest |

### Native tags and batch changes (added 2026-10-22)

- `tag list` lists existing category IDs and native My Tag labels. Keep the existing categories.
- `library search/info/dump` include string IDs, album, genre, actual musical key, BPM,
  duration_seconds/duration_ms, comment, my_tags, rating, year and file path.
- `--db PATH` is a root option, before the subcommand; use a snapshot for testing.
- Metadata writes **preview by default**. `--apply` requires a closed Rekordbox and backup.
  There is no force/no-backup option for these commands. Audio files are never modified.
- `--append-comment` preserves existing notes and deduplicates the annotation. `--comment`
  replaces the whole comment; use it only when replacement is intended.
- `--label NAME` sets the native record-label field (separate from My Tag); `--clear-label`
  clears it. Exports include `label` and `label_id`. Preserve an existing label unless replacement
  is intended. Batch manifests support `label` (nonempty string/null), `expected_label`, and
  `expected_artist`. Undo restores label assignments as well as comments and tag links.
- `--add-tag CATEGORY_ID NAME` reuses/creates a label under an existing category and links it.
  `--remove-tag CATEGORY_ID NAME` detaches it from the track only.
- Batch JSON: `{"schema_version":1,"changes":[{"track_id":"123","expected_title":"Track A",
  "append_comment":"Anime: Work A","add_tags":[{"category_id":"4","name":"Work A"}]}]}`.
  Query actual IDs first. Do not assume the example IDs/category names match a user's library.
- Other supported fields: `comment` (string/null), `remove_tags`, `expected_comment`,
  `expected_tags` (the entire current array). Unknown fields and duplicate track IDs are rejected.
- An applied operation returns backup paths and `undo_file`. Preview/apply that file with
  `library apply`. Undo refuses a different database or later comment/tag changes.
  It restores links/comments while keeping any newly created tag definitions.
- Use Codex to research anime associations and generate plans; do not infer uncertain matches
  as facts. No separate AI classifier is built into this CLI.
- Collection removal is not implemented. Existing playlist writes below are immediate commands.

### Playlist
| Command | Description |
|---------|-------------|
| `list` | All playlists |
| `create NAME [--force] [--no-backup]` | New playlist |
| `add NAME --track-title T [--force] [--no-backup]` | Add track |
| `clear NAME [--force] [--no-backup]` | Empty a playlist |

Playlist writes create a `master.db` backup before mutation. They refuse to run
while Rekordbox is open unless `--force` is supplied; forced writes still require
a backup. `--no-backup` is only accepted when Rekordbox is closed.

### Deck (live MIDI)
| Command | Description |
|---------|-------------|
| `play --deck N` | Play/pause |
| `sync --deck N` | Tempo sync |
| `crossfade FROM TO --secs S` | Smooth crossfade |
| `eq --deck N --hi --mid --lo` | EQ control |
| `hot-cue --deck N --slot 1-8` | Trigger hot cue |

### Top-level
| Command | Description |
|---------|-------------|
| `status` | Runtime / DB / MIDI state |
| `install-mapping` | Drop Bunker.midi.csv into rekordbox's MidiMappings folder |
| `mix A B --secs S` | Search two tracks and print manual loading/crossfade instructions |

## How it works

```
+------------------+
|   Your Agent     |
+--------+---------+
         |
         v
+------------------+
| cli-anything-    |
| rekordbox CLI    |
+--------+---------+
   |          |
   v          v
+----------+  +----------+
|pyrekord- |  |  mido +  |
|box DB    |  |  virtual |
|writes    |  |  MIDI    |
+----------+  +----------+
   |               |
   v               v
+----------+  +-----------+
| master.db|  | Rekordbox |
|SQLCipher |  | live decks|
+----------+  +-----------+
```

- **master.db** SQLCipher access is handled by pyrekordbox 0.5.x.
- **Virtual MIDI** mapping uses Pioneer's standard `.midi.csv` format; this CLI ships `Bunker.midi.csv` and an `install-mapping` command to drop it into rekordbox's `MidiMappings/` folder

## JSON output

Every command supports `--json`:
```bash
$ cli-anything-rekordbox --json library count
{"track_count": 30344}
```

## License
MIT

Original upstream notice preserved. The repository-root LICENSE is Apache-2.0;
upstream issue #475 / PR #498 track the conflicting package metadata.
