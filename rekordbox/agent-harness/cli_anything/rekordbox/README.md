# cli-anything-rekordbox

This fork adds library metadata management (2026-10-22).
See [the Korean library guide](../../LIBRARY_KO.md) in the source checkout.
No CLI Hub or MIDI driver is needed for library commands.

Agent-native command-line interface for Pioneer Rekordbox 6/7. Provides programmatic access to:
1. The encrypted master.db library (tracks, playlists, cues, hot cues)
2. Live deck control via virtual MIDI (play/pause, sync, crossfade, EQ, hot cues)

## Install

```bash
pip install -e .  # from rekordbox/agent-harness
# Optional live MIDI control:
pip install -e '.[midi]'
# Optional Windows extras for UI automation:
pip install cli-anything-rekordbox[windows]
```

Requires Python 3.11+, Rekordbox 6 or 7, and (optionally) a virtual MIDI driver for live-deck control.

## Why

Pioneer ships no public REST API for playback. This harness combines `pyrekordbox` (direct SQLCipher DB access) with `mido` (virtual MIDI) into a single CLI for AI agents.

## Quick start

```bash
cli-anything-rekordbox status
cli-anything-rekordbox library count
cli-anything-rekordbox library search "Daft Punk"
cli-anything-rekordbox --json tag list
cli-anything-rekordbox --json library update TRACK_ID --append-comment "Anime: Work A" --add-tag 4 "Work A"
# New metadata commands preview by default; --apply writes with a backup and undo plan.
cli-anything-rekordbox --json library apply changes.json --apply
cli-anything-rekordbox playlist create "MyMix"
cli-anything-rekordbox playlist add "MyMix" --track-title "One More Time"
cli-anything-rekordbox install-mapping
cli-anything-rekordbox deck crossfade 1 2 --secs 16
```

Playlist writes are guarded: the CLI creates a `master.db` backup before
mutation and refuses to write while Rekordbox is running unless `--force` is
provided. `--no-backup` is only accepted when Rekordbox is closed.

## License
MIT

Upstream license metadata is inconsistent: the repository-root LICENSE is Apache-2.0,
while this original package notice says MIT (upstream issue #475). This fork retains
the original notices and the repository-root license; it does not claim relicensing.
