"""Exercise real encrypted SQLite/ORM transactions; never access the user's DB."""
import hashlib
import json
from datetime import datetime
from pathlib import Path

import pytest
from click.testing import CliRunner
from pyrekordbox import MasterDatabase
from pyrekordbox.masterdb import models as m
from sqlalchemy import MetaData, text

from cli_anything.rekordbox import rekordbox_cli as rb
from cli_anything.rekordbox.core import metadata_cli


@pytest.fixture
def library_db(tmp_path, monkeypatch):
    path = tmp_path / "master.db"
    path.touch()
    db = MasterDatabase(path=path)
    schema = MetaData()
    for table in m.Base.metadata.tables.values():
        copied = table.to_metadata(schema)
        for column in copied.columns:
            if not column.primary_key:
                column.nullable = True
    schema.create_all(db.engine)
    with db.engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA journal_mode=WAL")
    rows = [
        m.AgentRegistry.create(registry_id="localUpdateCount", int_1=10),
        m.DjmdArtist.create(ID="artist", Name="Artist A"),
        m.DjmdAlbum.create(ID="album", Name="Album A"),
        m.DjmdKey.create(ID="key", ScaleName="Am"),
        m.DjmdContent.create(ID="123", Title="Track A", ArtistID="artist", AlbumID="album",
                             KeyID="key", BPM=12850, Length=180, Commnt="Original note",
                             FolderPath="F:/Music/track.mp3"),
        m.DjmdContent.create(ID="456", Title="Track B", Commnt=None),
        m.DjmdMyTag.create(ID="4", UUID="4", Name="Works", Attribute=1, ParentID="root", Seq=4),
        m.DjmdMyTag.create(ID="tag", Name="Existing", Attribute=0, ParentID="4", Seq=1),
        m.DjmdSongMyTag.create(ID="link", MyTagID="tag", ContentID="123", TrackNo=1),
    ]
    for row in rows:
        for column in row.__table__.columns:
            if isinstance(column.type, m.DateTime) and getattr(row, column.name) is None:
                setattr(row, column.name, datetime.now())
    db.session.add_all(rows)
    db.session.commit()
    db.registry.clear_buffer()
    rb._close_db(db)
    monkeypatch.setattr(rb, "_is_rekordbox_running", lambda: False)
    return path


def invoke(path, *args):
    return CliRunner().invoke(rb.cli, ["--json", "--db", str(path), *args])


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def state(path, track_id="123"):
    result = invoke(path, "library", "info", track_id)
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def write_manifest(tmp_path, changes):
    path = tmp_path / "batch.json"
    path.write_text(json.dumps({"schema_version": 1, "changes": changes}, ensure_ascii=False), encoding="utf-8")
    return path


def test_export_has_real_key_seconds_and_unicode(library_db, tmp_path):
    out = tmp_path / "tracks.json"
    result = invoke(library_db, "library", "dump", "--out", str(out))
    assert result.exit_code == 0, result.output
    row = next(r for r in json.loads(out.read_text(encoding="utf-8")) if r["id"] == "123")
    assert row["key"] == "Am"
    assert row["bpm"] == 128.5
    assert row["duration_seconds"] == 180
    assert row["duration_ms"] == 180000
    assert row["album"] == "Album A"
    assert row["my_tags"] == [{"category_id": "4", "name": "Existing"}]


def test_preview_does_not_write_or_create_backup(library_db):
    before = digest(library_db)
    result = invoke(library_db, "library", "update", "123", "--append-comment", "작품: テスト",
                    "--add-tag", "4", "작품 A")
    assert result.exit_code == 0, result.output
    plan = json.loads(result.output)
    assert plan["applied"] is False
    assert plan["create_tags"] == [{"category_id": "4", "name": "작품 A"}]
    assert digest(library_db) == before
    assert not (library_db.parent / "cli-anything-backups").exists()


def test_apply_preserves_comment_and_links_and_can_undo(library_db):
    before = state(library_db)
    original_hash = digest(library_db)
    result = invoke(library_db, "library", "update", "123", "--append-comment", "작품: テスト",
                    "--add-tag", "4", "작품 A", "--apply")
    assert result.exit_code == 0, result.output
    plan = json.loads(result.output)
    assert plan["applied"] is True
    assert digest(Path(plan["backup"][0])) == original_hash
    after = state(library_db)
    assert after["comment"] == "Original note\n작품: テスト"
    assert len(after["my_tags"]) == 2
    result = invoke(library_db, "library", "apply", plan["undo_file"], "--apply")
    assert result.exit_code == 0, result.output
    assert state(library_db) == before
    # All affected rows receive a local update sequence for Rekordbox to notice.
    with MasterDatabase(path=library_db) as db:
        assert db.get_content(ID="123").rb_local_usn > 10
        assert db.registry.get_local_update_count() > 10


def test_repeating_annotation_and_tag_is_noop(library_db):
    args = ("library", "update", "123", "--append-comment", "work: A\nrole: OP",
            "--add-tag", "4", "작품 A", "--apply")
    first = invoke(library_db, *args)
    assert first.exit_code == 0, first.output
    before = digest(library_db)
    second = invoke(library_db, *args)
    assert second.exit_code == 0, second.output
    assert json.loads(second.output)["changed_tracks"] == 0
    assert digest(library_db) == before


def test_batch_reuses_tag_and_updates_two_tracks(library_db, tmp_path):
    manifest = write_manifest(tmp_path, [
        {"track_id": "123", "add_tags": [{"category_id": "4", "name": "Shared"}]},
        {"track_id": "456", "append_comment": "새 메모", "add_tags": [{"category_id": "4", "name": "Shared"}]},
    ])
    result = invoke(library_db, "library", "apply", str(manifest), "--apply")
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["changed_tracks"] == 2
    with MasterDatabase(path=library_db) as db:
        assert db.get_my_tag(Name="Shared").count() == 1
        tag = db.get_my_tag(Name="Shared").one()
        assert db.get_my_tag_songs(MyTagID=tag.ID).count() == 2
        assert db.get_my_tag_songs(MyTagID=tag.ID).first().rb_local_usn > 10


@pytest.mark.parametrize("bad_change", [
    {"track_id": "missing", "comment": "bad"},
    {"track_id": "456", "unknown": True},
    {"track_id": "456", "comment": "x", "append_comment": "y"},
    {"track_id": "456", "add_tags": [{"category_id": "missing", "name": "x"}]},
    {"track_id": "456", "expected_title": "wrong", "comment": "bad"},
    {"track_id": "456", "expected_comment": "stale", "comment": "bad"},
    {"track_id": "456", "expected_tags": [{"category_id": "4", "name": "wrong"}]},
    {"track_id": "456", "add_tags": [{"category_id": "4", "name": "x", "typo": 1}]},
])
def test_invalid_batch_never_partially_writes(library_db, tmp_path, bad_change):
    before = digest(library_db)
    manifest = write_manifest(tmp_path, [{"track_id": "123", "comment": "should not persist"}, bad_change])
    result = invoke(library_db, "library", "apply", str(manifest), "--apply")
    assert result.exit_code != 0
    assert digest(library_db) == before
    assert not (library_db.parent / "cli-anything-backups").exists()


def test_write_failure_rolls_back_entire_transaction(library_db, tmp_path, monkeypatch):
    def fail_after_staging(db, plan):
        from cli_anything.rekordbox.core.metadata import execute_plan
        execute_plan(db, plan)
        raise OSError("simulated failure before commit")
    monkeypatch.setattr(metadata_cli, "execute_plan", fail_after_staging)
    before = digest(library_db)
    result = invoke(library_db, "library", "update", "123", "--comment", "changed",
                    "--add-tag", "4", "new", "--apply")
    assert result.exit_code != 0
    assert "simulated failure" in result.output
    assert digest(library_db) == before
    assert state(library_db)["comment"] == "Original note"


def test_write_refuses_running_rekordbox(library_db, monkeypatch):
    monkeypatch.setattr(rb, "_is_rekordbox_running", lambda: True)
    before = digest(library_db)
    result = invoke(library_db, "library", "update", "123", "--comment", "bad", "--apply")
    assert result.exit_code != 0
    assert "Close Rekordbox" in result.output
    assert digest(library_db) == before


def test_rekordbox_starting_before_commit_rolls_back(library_db, monkeypatch):
    states = iter([False, True])
    monkeypatch.setattr(rb, "_is_rekordbox_running", lambda: next(states))
    before = digest(library_db)
    result = invoke(library_db, "library", "update", "123", "--comment", "bad", "--apply")
    assert result.exit_code != 0
    assert "rolled back" in result.output
    assert digest(library_db) == before


def test_undo_refuses_to_overwrite_later_edits(library_db):
    first = invoke(library_db, "library", "update", "123", "--comment", "first", "--apply")
    assert first.exit_code == 0, first.output
    undo = json.loads(first.output)["undo_file"]
    assert invoke(library_db, "library", "update", "123", "--comment", "later", "--apply").exit_code == 0
    result = invoke(library_db, "library", "apply", undo, "--apply")
    assert result.exit_code != 0
    assert state(library_db)["comment"] == "later"


def test_undo_refuses_different_database(library_db, tmp_path):
    first = invoke(library_db, "library", "update", "123", "--comment", "first", "--apply")
    assert first.exit_code == 0, first.output
    undo = Path(json.loads(first.output)["undo_file"])
    data = json.loads(undo.read_text(encoding="utf-8"))
    data["database"] = str(tmp_path / "other.db")
    undo.write_text(json.dumps(data), encoding="utf-8")
    result = invoke(library_db, "library", "apply", str(undo), "--apply")
    assert result.exit_code != 0
    assert "different database" in result.output


def test_query_only_connection_blocks_accidental_writes(library_db):
    @rb.cli.command("probe-read-only", hidden=True)
    def probe():
        db = rb._open_db()
        assert db.session.execute(text("PRAGMA query_only")).scalar() == 1
        db.session.execute(text("UPDATE djmdContent SET Title='bad' WHERE ID='123'"))
    before = digest(library_db)
    result = invoke(library_db, "probe-read-only")
    assert result.exit_code != 0
    assert digest(library_db) == before
    rb.cli.commands.pop("probe-read-only")


def test_tag_detach_preserves_definition(library_db):
    result = invoke(library_db, "library", "update", "123", "--remove-tag", "4", "Existing", "--apply")
    assert result.exit_code == 0, result.output
    assert state(library_db)["my_tags"] == []
    tags = invoke(library_db, "tag", "list")
    assert any(t["name"] == "Existing" for t in json.loads(tags.output))


def test_backup_preserves_uncheckpointed_wal(library_db):
    writer = MasterDatabase(path=library_db)
    try:
        writer.get_content(ID="123").Commnt = "Previously committed WAL note"
        writer.session.commit()
        writer.registry.clear_buffer()
        assert Path(str(library_db) + "-wal").stat().st_size > 0
        result = invoke(library_db, "library", "update", "123", "--comment", "New note", "--apply")
        assert result.exit_code == 0, result.output
        backups = json.loads(result.output)["backup"]
        assert any(p.endswith("-wal") for p in backups)
        assert state(Path(backups[0]))["comment"] == "Previously committed WAL note"
    finally:
        rb._close_db(writer)


def test_backup_failure_prevents_changes(library_db, monkeypatch):
    def fail(db):
        raise PermissionError("backup unavailable")
    monkeypatch.setattr(rb, "_backup_database", fail)
    before = state(library_db)
    result = invoke(library_db, "library", "update", "123", "--comment", "bad", "--apply")
    assert result.exit_code != 0
    assert "backup unavailable" in result.output
    assert state(library_db) == before


def test_playlist_add_uses_string_track_id(library_db):
    created = invoke(library_db, "playlist", "create", "Set A")
    assert created.exit_code == 0, created.output
    added = invoke(library_db, "playlist", "add", "Set A", "--track-id", "123")
    assert added.exit_code == 0, added.output
    with MasterDatabase(path=library_db) as db:
        playlist = db.get_playlist(Name="Set A").one()
        assert [s.ContentID for s in playlist.Songs] == ["123"]


def test_library_discovery_uses_settings_when_install_is_on_other_drive(tmp_path, monkeypatch):
    from pyrekordbox import config
    app_dir = tmp_path / "Pioneer"
    settings_dir = app_dir / "rekordbox"
    settings_dir.mkdir(parents=True)
    relocated = tmp_path / "relocated-library"
    (settings_dir / "rekordbox3.settings").write_text(
        f'<PROPERTIES><VALUE name="masterDbDirectory" val="{relocated.as_posix()}"/></PROPERTIES>',
        encoding="utf-8")
    monkeypatch.setattr(config, "get_config", lambda version: {})
    monkeypatch.setattr(config, "get_pioneer_app_dir", lambda: app_dir)
    assert Path(rb._discover_db_path()) == relocated / "master.db"


def test_label_preview_and_apply_reuse_and_undo(library_db, tmp_path):
    before = state(library_db)
    preview = invoke(library_db, "library", "update", "123", "--label", "약캐 토모자키 군")
    assert preview.exit_code == 0, preview.output
    assert json.loads(preview.output)["create_labels"] == ["약캐 토모자키 군"]
    assert state(library_db) == before
    manifest = write_manifest(tmp_path, [
        {"track_id": "123", "expected_artist": "Artist A", "expected_label": None, "label": "약캐 토모자키 군"},
        {"track_id": "456", "label": "약캐 토모자키 군"},
    ])
    applied = invoke(library_db, "library", "apply", str(manifest), "--apply")
    assert applied.exit_code == 0, applied.output
    plan = json.loads(applied.output)
    after = state(library_db)
    assert after["label"] == "약캐 토모자키 군"
    assert after["comment"] == before["comment"]
    assert after["my_tags"] == before["my_tags"]
    with MasterDatabase(path=library_db) as db:
        assert db.get_label(Name="약캐 토모자키 군").count() == 1
        assert db.get_content(ID="123").LabelID == db.get_content(ID="456").LabelID
    undone = invoke(library_db, "library", "apply", plan["undo_file"], "--apply")
    assert undone.exit_code == 0, undone.output
    assert state(library_db) == before
    assert state(library_db, "456")["label"] is None


@pytest.mark.parametrize("fields", [
    {"label": ""}, {"label": " "}, {"label": "x" * 256}, {"label": 42},
    {"label": "Anime", "expected_label": "stale"},
    {"label": "Anime", "expected_artist": "Wrong artist"},
])
def test_invalid_or_stale_labels_never_write(library_db, tmp_path, fields):
    before = state(library_db)
    manifest = write_manifest(tmp_path, [{"track_id": "123", **fields}])
    result = invoke(library_db, "library", "apply", str(manifest), "--apply")
    assert result.exit_code != 0
    assert state(library_db) == before


def test_label_idempotence_clear_and_stale_undo(library_db):
    first = invoke(library_db, "library", "update", "123", "--label", "Anime A", "--apply")
    assert first.exit_code == 0, first.output
    repeated = invoke(library_db, "library", "update", "123", "--label", "Anime A", "--apply")
    assert json.loads(repeated.output)["changed_tracks"] == 0
    assert invoke(library_db, "library", "update", "123", "--label", "Anime B", "--apply").exit_code == 0
    stale = invoke(library_db, "library", "apply", json.loads(first.output)["undo_file"], "--apply")
    assert stale.exit_code != 0
    assert state(library_db)["label"] == "Anime B"
    cleared = invoke(library_db, "library", "update", "123", "--clear-label", "--apply")
    assert cleared.exit_code == 0, cleared.output
    assert state(library_db)["label"] is None
