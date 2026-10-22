"""Preview-first CLI commands. Added for the Jaek-Kein fork, 2026-10-22."""
from __future__ import annotations

import json
from pathlib import Path

import click

from .metadata import PlanError, build_plan, execute_plan, list_tags, undo_manifest


def run_manifest(ctx, manifest, apply):
    from .. import rekordbox_cli as rb
    from sqlalchemy import text
    from sqlalchemy.exc import SQLAlchemyError

    db = None
    try:
        if apply and rb._is_rekordbox_running():
            raise click.ClickException("Close Rekordbox before applying metadata changes")
        db = rb._open_db(writable=apply)
        if apply:
            # Serialize CLI writers and validate against the state actually being changed.
            db.session.execute(text("BEGIN IMMEDIATE"))
        plan = build_plan(db, manifest)
        plan["applied"] = False
        if apply and plan["changed_tracks"]:
            backups = rb._backup_database(db)
            journal_dir = Path(backups[0]).parent
            undo_path = journal_dir / "undo.json"
            undo_path.write_text(json.dumps(undo_manifest(plan), ensure_ascii=False, indent=2), encoding="utf-8")
            (journal_dir / "changes.json").write_text(
                json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
            execute_plan(db, plan)
            if rb._is_rekordbox_running():
                raise click.ClickException("Rekordbox started during the operation; changes rolled back")
            rb._commit_db_write(db)
            plan.update(applied=True, backup=backups, undo_file=str(undo_path))
        return plan
    except (PlanError, OSError, ValueError, SQLAlchemyError) as exc:
        raise click.ClickException(str(exc)) from exc
    finally:
        if db is not None:
            if db.session is not None:
                db.rollback()
            db.registry.enable_tracking()
            rb._close_db(db)


@click.group()
def tag():
    """Inspect native My Tag categories and labels (no audio-file tags)."""


@tag.command("list")
@click.pass_context
def tag_list(ctx):
    """List category IDs and existing labels for update/apply manifests."""
    from .. import rekordbox_cli as rb
    db = rb._open_db()
    rb._emit(ctx, list_tags(db))


@click.command("update")
@click.argument("track_id")
@click.option("--comment", help="Replace the comment (empty string clears it).")
@click.option("--append-comment", help="Append an annotation while retaining the existing comment.")
@click.option("--label", help="Set the native record-label field (not My Tag); reuse/create the label name.")
@click.option("--clear-label", is_flag=True, help="Clear the native record-label field.")
@click.option("--add-tag", type=(str, str), multiple=True, metavar="CATEGORY_ID NAME",
              help="Attach a native My Tag, creating the label in an existing category if needed.")
@click.option("--remove-tag", type=(str, str), multiple=True, metavar="CATEGORY_ID NAME",
              help="Detach this label from the track; do not delete the label.")
@click.option("--apply", is_flag=True, help="Write changes with backup; default is preview only.")
@click.pass_context
def update(ctx, track_id, comment, append_comment, label, clear_label, add_tag, remove_tag, apply):
    """Preview or apply one track's comment and My Tag changes, using its exact ID."""
    from .. import rekordbox_cli as rb
    change = {"track_id": track_id}
    if label is not None and clear_label:
        raise click.UsageError("Use either --label or --clear-label, not both")
    if label is not None or clear_label:
        change["label"] = label
    if comment is not None:
        change["comment"] = comment
    if append_comment is not None:
        change["append_comment"] = append_comment
    if add_tag:
        change["add_tags"] = [{"category_id": c, "name": n} for c, n in add_tag]
    if remove_tag:
        change["remove_tags"] = [{"category_id": c, "name": n} for c, n in remove_tag]
    if len(change) == 1:
        raise click.UsageError("Provide a comment, label or tag change")
    rb._emit(ctx, run_manifest(ctx, {"schema_version": 1, "changes": [change]}, apply))


@click.command("apply")
@click.argument("manifest_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--apply", is_flag=True, help="Write the entire manifest atomically; default is preview only.")
@click.pass_context
def apply_changes(ctx, manifest_path, apply):
    """Preview/apply a UTF-8 JSON batch or an undo.json from a previous operation."""
    from .. import rekordbox_cli as rb
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise click.ClickException(f"Cannot read manifest: {exc}") from exc
    rb._emit(ctx, run_manifest(ctx, manifest, apply))
