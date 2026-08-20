"""Read an attribute without caring which shape the core used.

`briefs_list` returns some attributes at the top level of a row and most
inside a `fields` map that carries provenance: `{"value": ..., "source":
..., "readings": [...]}`. A reader that knows only one shape does not
fail -- it returns `None` and the caller reports "nothing here", which is
a different and false statement from "I could not find it".

That mistake has been made six times in this package. It is centralised
here so it can be made once, correctly, and guarded against by
`test_no_single_shape_reads`.
"""

from __future__ import annotations

from typing import Any, Mapping


def attr(brief: Mapping[str, Any], key: str, default: Any = None) -> Any:
    """One attribute, wherever the core chose to put it.

    Top level wins where both exist: it is the already-resolved value.
    `0` and `False` are values and are returned as such; only a genuinely
    absent key yields `default`.
    """
    if key in brief and brief[key] is not None:
        return brief[key]
    fields = brief.get("fields")
    if isinstance(fields, Mapping):
        entry = fields.get(key)
        if isinstance(entry, Mapping):
            value = entry.get("value")
            if value is not None:
                return value
    return default
