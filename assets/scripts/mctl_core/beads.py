"""Read-only adapters for canonical MathCity decision beads."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Iterable, Mapping
from uuid import uuid4


DEFAULT_BD_TIMEOUT_SECONDS = 30
BD_TIMEOUT_ENV = "MCTL_BD_TIMEOUT_SECONDS"
# bd reserves exit 13 for "an --if-status/--if-assignee guard no longer held".
BD_GUARD_MISMATCH_EXIT = 13
BD_LIST_ARGS = ("bd", "list", "--all", "--limit", "0", "--json", "--readonly")


def bd_timeout_seconds() -> int:
    """Seconds to allow a bd subprocess.

    A full read of the largest live rig already costs seconds, and a read
    is slowest exactly when the data plane is degraded -- the moment these
    commands are most useful. Keep the ceiling well clear of that, and let
    an operator raise it further per invocation.
    """
    raw = os.environ.get(BD_TIMEOUT_ENV)
    if raw is None:
        return DEFAULT_BD_TIMEOUT_SECONDS
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_BD_TIMEOUT_SECONDS
    return value if value > 0 else DEFAULT_BD_TIMEOUT_SECONDS


#: Slack left between the `bd` subprocess timeout and a caller's own deadline,
#: so the store reports "I could not answer" a beat before the caller reports
#: "the read went quiet". The store's sentence is the more useful one: it names
#: which of a multi-store read's lanes failed.
BD_DEADLINE_MARGIN_SECONDS = 2.0


def bd_timeout_within(remaining: float | None) -> int | None:
    """The `bd` timeout to use inside a caller's remaining wall-clock budget.

    The default above is 30s and the cross-rig fan-out's deadline is 25s, so
    a caller that just took the default always lost the race: the fan-out gave
    up first and reported that the *rig* went quiet, when the fact available
    one layer down was that the *bead store* did. This bounds the subprocess
    below whatever budget is actually left.

    It bounds, it does not raise: an operator who lowered
    `MCTL_BD_TIMEOUT_SECONDS` keeps the lower number. `None` remaining means
    the caller set no deadline, and the configured value stands.
    """
    configured = bd_timeout_seconds()
    if remaining is None:
        return configured
    return max(1, min(configured, int(remaining - BD_DEADLINE_MARGIN_SECONDS)))


@dataclass(frozen=True)
class Bead:
    id: str
    title: str
    status: str
    issue_type: str
    labels: tuple[str, ...]
    source_dependencies: tuple[str, ...]
    created_at: str | None
    updated_at: str | None
    raw: Mapping[str, object]
    assignee: str | None = None
    #: The bead's long-form body. For a decision bead this is the brief
    #: itself -- the evidence a verdict is given on -- so it is a typed
    #: field rather than something every caller digs out of `raw`.
    description: str | None = None

    @property
    def is_brief(self) -> bool:
        return self.issue_type == "decision"

    @property
    def has_active_assignee(self) -> bool:
        """Whether someone already holds this bead.

        Dispatching over an active assignee is the lost-claim case plan §4
        reserves MWRK001 for.
        """
        return bool(self.assignee and self.assignee.strip())

    @property
    def workflow_root_id(self) -> str | None:
        """The source bead this workflow bead hangs off, if any."""
        metadata = self.raw.get("metadata")
        if not isinstance(metadata, Mapping):
            return None
        root = metadata.get("gc.root_bead_id")
        return root if isinstance(root, str) and root else None

    @property
    def is_open(self) -> bool:
        return self.status.lower() in {"open", "hooked", "in_progress", "blocked", "review", "testing"}


class BeadReadError(RuntimeError):
    """The canonical bead source could not be read."""


class BeadWriteError(RuntimeError):
    """The canonical bead source could not be updated."""


class BeadRaceLostError(BeadWriteError):
    """Another actor changed the bead first, so the guarded write was skipped.

    bd exits 13 when an --if-status/--if-assignee guard no longer holds. It
    wrote nothing, and retrying the same guard cannot succeed.
    """


@dataclass(frozen=True)
class BeadRelate:
    """A bidirectional `relates_to` edge between two beads in ONE store.

    `bd dep relate`, deliberately not `bd dep add`. Measured against bd 1.1.0
    on 2026-08-20 with two isolated stores:

    * ``bd dep add <local> <foreign-or-unknown-id>`` exits **0**, prints
      "✓ Added dependency", and writes a row whose target nothing can resolve.
      ``bd show`` then reports ``dependency_count = 1`` beside
      ``dependencies = null``, and ``bd dep list`` returns ``[]``. The edge is
      lost in every hydrating read while the count still claims it is there.
    * ``bd dep relate <local> <foreign-or-unknown-id>`` exits **1** with
      "failed to resolve <id>: no issue found" and writes nothing.

    So `relate` does not share the silent-loss defect today. It is still not
    trusted here, for two reasons. `relate` resolves ids **fuzzily** -- a
    measured ``bd dep relate aa-e11 aa-c`` cheerfully linked ``aa-e11`` to
    ``aa-cfi`` -- so an exit code of 0 does not mean the edge connects the two
    ids that were asked for. And "the vendored binary currently fails loudly"
    is a property of a binary this repository does not own. `verify_relation`
    below re-reads the store and is what actually makes the guarantee.
    """

    source_id: str
    target_id: str
    link_type: str = "relates-to"

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "bead_relate",
            "link_type": self.link_type,
            "source_id": self.source_id,
            "target_id": self.target_id,
        }


@dataclass(frozen=True)
class RelationVerification:
    """What the canonical store says about an edge AFTER it was written.

    Two independent failures, kept apart because only one of them is the
    known bd defect:

    * `edge_recorded` false -- the store holds no row joining these two ids at
      all. The write did not land, whatever it exited.
    * `unresolved_endpoints` non-empty -- a row exists but names an id this
      store cannot resolve to a bead. That is the dangling cross-store edge:
      present in `bd list --all --json`, invisible to `bd show` and
      `bd dep list`, counted by `dependency_count`.
    """

    source_id: str
    target_id: str
    edge_recorded: bool
    unresolved_endpoints: tuple[str, ...]

    @property
    def verified(self) -> bool:
        return self.edge_recorded and not self.unresolved_endpoints

    def to_dict(self) -> dict[str, object]:
        return {
            "edge_recorded": self.edge_recorded,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "unresolved_endpoints": list(self.unresolved_endpoints),
            "verified": self.verified,
        }


def verify_relation(
    beads: Iterable[Bead], source_id: str, target_id: str
) -> RelationVerification:
    """Prove a relate edge exists in the canonical store and both ends resolve.

    Pure: it reads a bead listing that has already been fetched, so the same
    check runs against bd and against the fixture seam with no branch.

    The edge is accepted in either direction. `bd dep relate` writes both rows,
    but a store that recorded only one still recorded the relationship, and
    reporting that as a failed write would be wrong.
    """
    by_id = {bead.id: bead for bead in beads}

    def outgoing(bead_id: str) -> tuple[str, ...]:
        bead = by_id.get(bead_id)
        return bead.source_dependencies if bead is not None else ()

    forward = target_id in outgoing(source_id)
    reverse = source_id in outgoing(target_id)
    unresolved = tuple(
        bead_id for bead_id in (source_id, target_id) if bead_id not in by_id
    )
    return RelationVerification(
        source_id=source_id,
        target_id=target_id,
        edge_recorded=forward or reverse,
        unresolved_endpoints=unresolved,
    )


@dataclass(frozen=True)
class BeadUpdate:
    id: str
    status: str | None = None
    metadata: Mapping[str, str] | None = None
    defer_until: str | None = None
    # Optimistic-concurrency guard: the status observed when the plan was
    # built. bd writes nothing and exits 13 if it no longer holds.
    if_status: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.id,
            "metadata": dict(sorted((self.metadata or {}).items())),
        }
        if self.status is not None:
            payload["status"] = self.status
        if self.defer_until is not None:
            payload["defer_until"] = self.defer_until
        payload["if_status"] = self.if_status
        return payload


@dataclass(frozen=True)
class BeadCreate:
    """A canonical bead that does not exist yet.

    bd mints the id, so the plan that describes this write cannot name its own
    target. `placeholder_id` is the token the plan uses for the not-yet-known
    id; the apply step substitutes the real id into every derived path once bd
    has accepted the create.
    """

    placeholder_id: str
    title: str
    body: str
    issue_type: str = "decision"
    labels: tuple[str, ...] = ()
    metadata: Mapping[str, str] | None = None
    sources: tuple[str, ...] = ()
    source_link_type: str = "related"
    #: `issue_type="event"` only. bd rejects these three flags on every other
    #: type, so they are emitted only when the type is `event` rather than
    #: whenever they happen to be set.
    event_category: str | None = None
    event_target: str | None = None
    event_payload: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "issue_type": self.issue_type,
            "labels": list(self.labels),
            "metadata": dict(sorted((self.metadata or {}).items())),
            "placeholder_id": self.placeholder_id,
            "source_link_type": self.source_link_type,
            "sources": list(self.sources),
            "title": self.title,
        }
        for key in ("event_category", "event_target", "event_payload"):
            value = getattr(self, key)
            if value is not None:
                payload[key] = value
        return payload


def read_beads(
    rig_root: Path,
    *,
    fixture_path: Path | None = None,
    timeout: int | None = None,
) -> tuple[Bead, ...]:
    """Query the canonical bead store, or read an explicitly injected fixture."""
    if fixture_path is not None:
        return tuple(_bead_from_mapping(row) for row in _read_jsonl(fixture_path))
    return tuple(_bead_from_mapping(row) for row in _read_bd(rig_root, timeout or bd_timeout_seconds()))


def apply_bead_update(
    rig_root: Path,
    update: BeadUpdate,
    *,
    fixture_path: Path | None = None,
    timeout: int | None = None,
) -> dict[str, object]:
    """Apply one canonical bead update through the fixture seam or bd."""
    if fixture_path is not None:
        _apply_fixture_update(fixture_path, update)
        return {"id": update.id, "mode": "fixture"}
    return _apply_bd_update(rig_root, update, timeout or bd_timeout_seconds())


def apply_bead_create(
    rig_root: Path,
    create: BeadCreate,
    *,
    fixture_path: Path | None = None,
    timeout: int | None = None,
) -> dict[str, object]:
    """Create one canonical decision bead through the fixture seam or bd."""
    if fixture_path is not None:
        return _apply_fixture_create(fixture_path, create)
    return _apply_bd_create(rig_root, create, timeout or bd_timeout_seconds())


def apply_bead_relate(
    rig_root: Path,
    relate: BeadRelate,
    *,
    fixture_path: Path | None = None,
    timeout: int | None = None,
) -> dict[str, object]:
    """Write one bidirectional relate edge through the fixture seam or bd.

    This only *writes*. Whether the edge is really there afterwards is a
    separate question with a separate answer -- see `verify_relation`, and the
    measurements on `BeadRelate` for why the exit code is not that answer.
    """
    if fixture_path is not None:
        return _apply_fixture_relate(fixture_path, relate)
    return _apply_bd_relate(rig_root, relate, timeout or bd_timeout_seconds())


def _read_jsonl(path: Path) -> Iterable[Mapping[str, object]]:
    try:
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                value = json.loads(stripped)
                if not isinstance(value, dict):
                    raise BeadReadError(f"{path}:{line_number} is not a JSON object")
                yield value
    except (OSError, json.JSONDecodeError) as error:
        raise BeadReadError(f"Could not read bead export {path}: {error}") from error


def _read_bd(rig_root: Path, timeout: int) -> Iterable[Mapping[str, object]]:
    try:
        result = subprocess.run(
            list(BD_LIST_ARGS),
            cwd=rig_root,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise BeadReadError(f"Could not query beads through bd: {error}") from error
    if result.returncode != 0:
        raise BeadReadError(result.stderr.strip() or f"{' '.join(BD_LIST_ARGS)} failed")
    try:
        parsed: Any = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise BeadReadError(f"{' '.join(BD_LIST_ARGS)} returned invalid JSON: {error}") from error
    if not isinstance(parsed, list) or not all(isinstance(row, dict) for row in parsed):
        raise BeadReadError(f"{' '.join(BD_LIST_ARGS)} did not return a JSON list of objects")
    return parsed


def _apply_bd_update(rig_root: Path, update: BeadUpdate, timeout: int) -> dict[str, object]:
    args = ["bd", "update", update.id]
    if update.status is not None:
        args.extend(("--status", update.status))
    if update.defer_until is not None:
        args.extend(("--defer", update.defer_until))
    for key, value in sorted((update.metadata or {}).items()):
        args.extend(("--set-metadata", f"{key}={value}"))
    if update.if_status is not None:
        args.extend(("--if-status", update.if_status))
    args.append("--json")
    try:
        result = subprocess.run(
            args,
            cwd=rig_root,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise BeadWriteError(f"Could not update bead {update.id}: {error}") from error
    if result.returncode == BD_GUARD_MISMATCH_EXIT:
        raise BeadRaceLostError(
            f"another actor changed {update.id!r} before this write "
            f"(bd exit {BD_GUARD_MISMATCH_EXIT}; expected status "
            f"{update.if_status!r})"
        )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise BeadWriteError(detail or f"{' '.join(args)} failed")
    if not result.stdout.strip():
        return {"id": update.id, "mode": "bd", "stdout": ""}
    try:
        parsed: Any = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"id": update.id, "mode": "bd", "stdout": result.stdout.strip()}
    return {"id": update.id, "mode": "bd", "result": parsed}


def _apply_bd_relate(rig_root: Path, relate: BeadRelate, timeout: int) -> dict[str, object]:
    # `bd dep relate` answers in prose ("✓ Linked a ↔ b"), so only its exit
    # code is read. Parsing that sentence is the habit this whole surface
    # exists to remove.
    args = ["bd", "dep", "relate", relate.source_id, relate.target_id]
    _run_bd_command(
        rig_root,
        args,
        timeout,
        f"Could not relate {relate.source_id} to {relate.target_id}",
    )
    return {
        "mode": "bd",
        "source_id": relate.source_id,
        "target_id": relate.target_id,
    }


def _apply_bd_create(rig_root: Path, create: BeadCreate, timeout: int) -> dict[str, object]:
    args = ["bd", "create", create.title, "--type", create.issue_type]
    if create.body:
        args.extend(("--description", create.body))
    if create.labels:
        args.extend(("--labels", ",".join(create.labels)))
    if create.issue_type == "event":
        # bd refuses --event-* on any other type, so these are keyed on the
        # type rather than on "the caller happened to set them".
        for flag, value in (
            ("--event-category", create.event_category),
            ("--event-target", create.event_target),
            ("--event-payload", create.event_payload),
        ):
            if value is not None:
                args.extend((flag, value))
    if create.metadata:
        args.extend(("--metadata", json.dumps(dict(sorted(create.metadata.items())), sort_keys=True)))
    args.append("--json")
    failure = f"Could not create bead {create.title!r}"
    stdout = _run_bd_command(rig_root, args, timeout, failure)
    try:
        parsed: Any = json.loads(stdout)
    except json.JSONDecodeError as error:
        raise BeadWriteError(f"{failure}: bd returned invalid JSON: {error}") from error
    bead_id = parsed.get("id") if isinstance(parsed, dict) else None
    if not isinstance(bead_id, str) or not bead_id:
        raise BeadWriteError(f"bd create returned no bead id for {create.title!r}")
    # B2.1 wants the source link on the canonical bead, and bd has no
    # create-time `related` dependency flag, so the link is a second call.
    # bd link answers in prose, not JSON, so only its exit code is read.
    for source in create.sources:
        _run_bd_command(
            rig_root,
            ["bd", "link", bead_id, source, "--type", create.source_link_type],
            timeout,
            f"Could not link bead {bead_id} to source {source}",
        )
    return {"id": bead_id, "mode": "bd", "result": parsed}


def _run_bd_command(rig_root: Path, args: list[str], timeout: int, failure: str) -> str:
    try:
        result = subprocess.run(
            args,
            cwd=rig_root,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise BeadWriteError(f"{failure}: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise BeadWriteError(detail or f"{' '.join(args)} failed")
    return result.stdout


def _apply_fixture_create(path: Path, create: BeadCreate) -> dict[str, object]:
    rows = list(_read_jsonl(path))
    bead_id = _next_fixture_id(rows)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    row: dict[str, object] = {
        "id": bead_id,
        "title": create.title,
        "status": "open",
        "issue_type": create.issue_type,
        "labels": list(create.labels),
        "description": create.body,
        "dependencies": [
            {"issue_id": bead_id, "depends_on_id": source, "type": create.source_link_type}
            for source in create.sources
        ],
        "created_at": now,
        "updated_at": now,
    }
    if create.metadata:
        row["metadata"] = dict(sorted(create.metadata.items()))
    if create.issue_type == "event":
        for key in ("event_category", "event_target", "event_payload"):
            value = getattr(create, key)
            if value is not None:
                row[key] = value
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    return {"id": bead_id, "mode": "fixture", "result": row}


def _apply_fixture_relate(path: Path, relate: BeadRelate) -> dict[str, object]:
    """Write the edge into the fixture the way bd writes it into the store.

    Faithful on purpose, including the ugly part: bd records an edge row whose
    target does not exist, so this does too. A fixture that refused instead
    would make the dangling-edge case untestable without a second Dolt store,
    and the dangling-edge case is the one that matters.

    The *source* row is a different matter -- `_apply_fixture_update` already
    refuses to update a bead that is not there, and an edge hanging off a row
    that does not exist could not be written by bd either.
    """
    rows = list(_read_jsonl(path))
    ids = {row.get("id") for row in rows}
    if relate.source_id not in ids:
        raise BeadWriteError(f"No bead named {relate.source_id!r} exists in {path}")
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    pairs = [(relate.source_id, relate.target_id)]
    if relate.target_id in ids:
        # bd writes both directions, but only between rows it can resolve.
        pairs.append((relate.target_id, relate.source_id))
    rewritten: list[dict[str, object]] = []
    for row in rows:
        mutable = dict(row)
        for issue_id, depends_on in pairs:
            if mutable.get("id") != issue_id:
                continue
            dependencies = list(mutable.get("dependencies") or [])
            already = any(
                isinstance(entry, dict)
                and entry.get("issue_id") == issue_id
                and entry.get("depends_on_id") == depends_on
                for entry in dependencies
            )
            if not already:
                dependencies.append(
                    {
                        "issue_id": issue_id,
                        "depends_on_id": depends_on,
                        "type": relate.link_type,
                        "created_at": now,
                    }
                )
            mutable["dependencies"] = dependencies
        rewritten.append(mutable)
    path.write_text(
        "".join(f"{json.dumps(row, sort_keys=True)}\n" for row in rewritten),
        encoding="utf-8",
    )
    return {
        "mode": "fixture",
        "source_id": relate.source_id,
        "target_id": relate.target_id,
    }


def _next_fixture_id(rows: list[Mapping[str, object]]) -> str:
    """Mint a fixture bead id that looks like one the rig's prefix would."""
    prefix = "mc"
    for row in rows:
        candidate = row.get("id")
        if isinstance(candidate, str) and "-" in candidate:
            prefix = candidate.split("-", 1)[0]
            break
    return f"{prefix}-{uuid4().hex[:7]}"


def _apply_fixture_update(path: Path, update: BeadUpdate) -> None:
    rows = list(_read_jsonl(path))
    changed = False
    rewritten: list[dict[str, object]] = []
    for row in rows:
        mutable = dict(row)
        if mutable.get("id") == update.id:
            if update.status is not None:
                mutable["status"] = update.status
            if update.defer_until is not None:
                mutable["defer_until"] = update.defer_until
            metadata = mutable.get("metadata")
            if not isinstance(metadata, dict):
                metadata = {}
            metadata = dict(metadata)
            metadata.update(update.metadata or {})
            if metadata:
                mutable["metadata"] = metadata
            changed = True
        rewritten.append(mutable)
    if not changed:
        raise BeadWriteError(f"No bead named {update.id!r} exists in {path}")
    path.write_text(
        "".join(f"{json.dumps(row, sort_keys=True)}\n" for row in rewritten),
        encoding="utf-8",
    )


def _bead_from_mapping(raw: Mapping[str, object]) -> Bead:
    bead_id = _string(raw, "id")
    if not bead_id:
        raise BeadReadError("A bead has no string id")
    dependencies = raw.get("dependencies", ())
    source_dependencies = tuple(sorted(_dependency_ids(bead_id, dependencies)))
    return Bead(
        id=bead_id,
        title=_string(raw, "title") or bead_id,
        status=_string(raw, "status") or "open",
        issue_type=_string(raw, "issue_type") or _string(raw, "type") or "",
        labels=tuple(sorted(_strings(raw.get("labels", ())))),
        source_dependencies=source_dependencies,
        created_at=_string(raw, "created_at"),
        updated_at=_string(raw, "updated_at"),
        raw=raw,
        assignee=_string(raw, "assignee"),
        description=_string(raw, "description"),
    )


def _dependency_ids(bead_id: str, value: object) -> Iterable[str]:
    if not isinstance(value, list):
        return ()
    ids: list[str] = []
    for dependency in value:
        if isinstance(dependency, str):
            ids.append(dependency)
        elif isinstance(dependency, dict):
            issue_id = dependency.get("issue_id")
            depends_on = _first_string(
                dependency,
                ("depends_on_id", "depends_on_issue_id", "depends_on", "source_id"),
            )
            if issue_id == bead_id and depends_on:
                ids.append(depends_on)
                continue
            if issue_id is None and depends_on:
                ids.append(depends_on)
                continue
            if issue_id != bead_id and isinstance(issue_id, str) and issue_id and depends_on is None:
                ids.append(issue_id)
                continue
            fallback = _first_string(dependency, ("id",))
            if fallback:
                ids.append(fallback)
    return ids


def _first_string(value: Mapping[str, object], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate:
            return candidate
    return None


def _string(value: Mapping[str, object], key: str) -> str | None:
    candidate = value.get(key)
    return candidate if isinstance(candidate, str) and candidate else None


def _strings(value: object) -> Iterable[str]:
    if isinstance(value, list):
        return (item for item in value if isinstance(item, str) and item)
    return ()
