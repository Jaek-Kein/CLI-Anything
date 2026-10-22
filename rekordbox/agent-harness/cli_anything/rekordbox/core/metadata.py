"""Library metadata plans. Modified for the Jaek-Kein fork, 2026-10-22.

Plans use stable track IDs and native My Tag categories. No audio files are edited.
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4


class PlanError(ValueError):
    """An invalid or stale change plan; nothing should be committed."""


def _models():
    from pyrekordbox.masterdb import models
    return models


def content_query(db):
    """Load export relationships in batches instead of one query per track."""
    from sqlalchemy.orm import selectinload
    m = _models()
    return db.get_content().options(
        selectinload(m.DjmdContent.Artist), selectinload(m.DjmdContent.Album),
        selectinload(m.DjmdContent.Genre), selectinload(m.DjmdContent.Key),
        selectinload(m.DjmdContent.Label),
        selectinload(m.DjmdContent.MyTags).selectinload(m.DjmdSongMyTag.MyTag),
    )


def tag_ref(tag):
    return {"category_id": str(tag.ParentID), "name": tag.Name}


def _sort_refs(refs):
    return sorted(refs, key=lambda r: (r["category_id"], r["name"]))


def track_state(track):
    return {
        "comment": track.Commnt,
        "label": track.LabelName,
        "tags": _sort_refs([tag_ref(link.MyTag) for link in track.MyTags if link.MyTag is not None]),
    }


def serialize_track(track):
    state = track_state(track)
    seconds = track.Length
    return {
        "id": str(track.ID), "title": track.Title, "artist": track.ArtistName,
        "album": track.AlbumName, "genre": track.GenreName,
        "bpm": track.BPM / 100.0 if track.BPM else None,
        "key": track.KeyName, "duration_seconds": seconds,
        "duration_ms": seconds * 1000 if seconds is not None else None,
        "comment": state["comment"], "my_tags": state["tags"],
        "label": state["label"], "label_id": track.LabelID,
        "rating": track.Rating, "year": track.ReleaseYear, "file": track.FolderPath,
    }


def list_tags(db):
    tags = list(db.get_my_tag())
    names = {str(t.ID): t.Name for t in tags}
    return [
        {"id": str(t.ID), "name": t.Name, "category_id": str(t.ParentID),
         "category": names.get(str(t.ParentID)), "is_category": t.Attribute == 1,
         "sequence": t.Seq}
        for t in sorted(tags, key=lambda t: (str(t.ParentID), t.Seq or 0, str(t.ID)))
    ]


def database_path(db):
    return str(Path(db.engine.url.database).resolve())


def _identity(value):
    return os.path.normcase(str(Path(value).resolve()))


def _id(value, label):
    if isinstance(value, bool) or not isinstance(value, (str, int)) or not str(value).strip():
        raise PlanError(f"{label} must be a nonempty string or integer")
    return str(value)


def _refs(value, label):
    if not isinstance(value, list):
        raise PlanError(f"{label} must be an array")
    result = set()
    for ref in value:
        if not isinstance(ref, dict) or set(ref) != {"category_id", "name"}:
            raise PlanError(f"{label} entries require exactly category_id and name")
        category = _id(ref["category_id"], "category_id")
        name = ref["name"]
        if not isinstance(name, str) or not name.strip() or len(name) > 255:
            raise PlanError("Tag names must contain 1..255 characters")
        result.add((category, name))
    return result


def _as_refs(pairs):
    return [{"category_id": c, "name": n} for c, n in sorted(pairs)]


def build_plan(db, manifest):
    """Validate the entire manifest without mutating ORM objects or files."""
    if not isinstance(manifest, dict) or set(manifest) - {"schema_version", "database", "changes"}:
        raise PlanError("Manifest requires schema_version=1 and changes; unknown fields are rejected")
    if type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 1:
        raise PlanError("schema_version must be 1")
    if "database" in manifest:
        if not isinstance(manifest["database"], str) or _identity(manifest["database"]) != _identity(database_path(db)):
            raise PlanError("Manifest belongs to a different database")
    changes = manifest.get("changes")
    if not isinstance(changes, list) or not changes:
        raise PlanError("changes must be a nonempty array")
    tags = list(db.get_my_tag())
    categories = {str(t.ID) for t in tags if t.Attribute == 1}
    existing = {}
    for tag in tags:
        if tag.Attribute != 0:
            continue
        key = (str(tag.ParentID), tag.Name)
        if key in existing:
            raise PlanError(f"Duplicate native tag names in category {key[0]}: {key[1]!r}")
        existing[key] = tag
    allowed = {"track_id", "expected_title", "expected_artist", "expected_comment", "expected_tags",
               "expected_label", "label", "comment", "append_comment", "add_tags", "remove_tags"}
    seen, planned, new_tags, new_labels = set(), [], set(), set()
    for change in changes:
        if not isinstance(change, dict) or set(change) - allowed:
            raise PlanError("Each change must be an object containing only supported fields")
        track_id = _id(change.get("track_id"), "track_id")
        if track_id in seen:
            raise PlanError(f"Duplicate track_id {track_id}; combine its changes into one entry")
        seen.add(track_id)
        track = db.get_content(ID=track_id)
        if track is None:
            raise PlanError(f"Track {track_id} not found")
        if "expected_title" in change and change["expected_title"] != track.Title:
            raise PlanError(f"Track {track_id}: title changed or wrong track ID")
        if "expected_artist" in change and change["expected_artist"] != track.ArtistName:
            raise PlanError(f"Track {track_id}: artist changed or wrong track ID")
        before = track_state(track)
        before_pairs = _refs(before["tags"], "stored tags")
        if "expected_comment" in change and change["expected_comment"] != before["comment"]:
            raise PlanError(f"Track {track_id}: comment changed since the plan was created")
        if "expected_tags" in change and _refs(change["expected_tags"], "expected_tags") != before_pairs:
            raise PlanError(f"Track {track_id}: tags changed since the plan was created")
        if "expected_label" in change and change["expected_label"] != before["label"]:
            raise PlanError(f"Track {track_id}: label changed since the plan was created")
        label = change.get("label", before["label"])
        if "label" in change and label is not None:
            if not isinstance(label, str) or not label.strip() or len(label) > 255:
                raise PlanError("label must be a nonempty string of at most 255 characters, or null")
            label_rows = db.get_label(Name=label).all()
            if len(label_rows) > 1:
                raise PlanError(f"Duplicate native label name: {label!r}")
            if not label_rows:
                new_labels.add(label)
        if "comment" in change and "append_comment" in change:
            raise PlanError("Use either comment or append_comment, not both")
        comment = before["comment"]
        if "comment" in change:
            comment = change["comment"]
            if comment is not None and not isinstance(comment, str):
                raise PlanError("comment must be a string or null")
        if "append_comment" in change:
            addition = change["append_comment"]
            if not isinstance(addition, str) or not addition.strip():
                raise PlanError("append_comment must be a nonempty string")
            # Repeated execution must not append the same annotation twice.
            if f"\n{addition}\n" not in f"\n{comment or ''}\n":
                comment = f"{comment}\n{addition}" if comment else addition
        added = _refs(change.get("add_tags", []), "add_tags")
        removed = _refs(change.get("remove_tags", []), "remove_tags")
        if added & removed:
            raise PlanError("A tag cannot be added and removed in the same change")
        for category, _ in added | removed:
            if category not in categories:
                raise PlanError(f"Unknown native My Tag category {category}; run tag list")
        new_tags.update(added - existing.keys())
        after = {"comment": comment, "label": label, "tags": _as_refs((before_pairs | added) - removed)}
        planned.append({"track_id": track_id, "title": track.Title, "artist": track.ArtistName,
                        "before": before, "after": after, "changed": before != after})
    return {"schema_version": 1, "database": database_path(db),
            "changed_tracks": sum(p["changed"] for p in planned),
            "create_tags": _as_refs(new_tags), "create_labels": sorted(new_labels), "changes": planned}


def undo_manifest(plan):
    """Undo only these links/comments, refusing to overwrite subsequent changes."""
    changes = []
    for row in plan["changes"]:
        if not row["changed"]:
            continue
        before, after = row["before"], row["after"]
        old = _refs(before["tags"], "before")
        new = _refs(after["tags"], "after")
        changes.append({
            "track_id": row["track_id"], "expected_title": row["title"],
            "expected_artist": row["artist"],
            "expected_comment": after["comment"], "expected_tags": after["tags"],
            "expected_label": after["label"], "label": before["label"],
            "comment": before["comment"],
            "add_tags": _as_refs(old - new), "remove_tags": _as_refs(new - old),
        })
    return {"schema_version": 1, "database": plan["database"], "changes": changes}


def execute_plan(db, plan):
    """Stage a previously validated plan; the caller owns backup/commit/rollback."""
    m = _models()
    for name in plan["create_labels"]:
        db.add_label(name)
    labels = {label.Name: label for label in db.get_label()}
    for ref in plan["create_tags"]:
        parent, name = ref["category_id"], ref["name"]
        siblings = list(db.get_my_tag(ParentID=parent))
        tag = m.DjmdMyTag.create(
            ID=str(db.generate_unused_id(m.DjmdMyTag, is_28_bit=False)),
            UUID=str(uuid4()), ParentID=parent, Name=name, Attribute=0,
            Seq=max((t.Seq or 0 for t in siblings), default=0) + 1,
        )
        db.add(tag)
        db.flush()
    tags = {(str(t.ParentID), t.Name): t for t in db.get_my_tag() if t.Attribute == 0}
    for row in plan["changes"]:
        if not row["changed"]:
            continue
        track = db.get_content(ID=row["track_id"])
        if row["before"]["comment"] != row["after"]["comment"]:
            track.Commnt = row["after"]["comment"]
        if row["before"]["label"] != row["after"]["label"]:
            label_name = row["after"]["label"]
            track.LabelID = labels[label_name].ID if label_name is not None else None
        old = _refs(row["before"]["tags"], "before")
        new = _refs(row["after"]["tags"], "after")
        for key in old - new:
            tag = tags[key]
            for link in db.get_my_tag_songs(ContentID=track.ID, MyTagID=tag.ID):
                db.delete(link)
        for key in new - old:
            tag = tags[key]
            siblings = list(db.get_my_tag_songs(MyTagID=tag.ID))
            link = m.DjmdSongMyTag.create(
                ID=str(uuid4()), UUID=str(uuid4()), MyTagID=tag.ID, ContentID=track.ID,
                TrackNo=max((s.TrackNo or 0 for s in siblings), default=0) + 1,
            )
            db.add(link)
        track.updated_at = datetime.now()
    db.flush()
