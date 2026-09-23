"""Stacks Project MCP server.

Tools:
  get_tag       — fetch statement (and optionally proof) for a tag
  search_stacks — keyword search returning matching tags with previews
  tag_info      — metadata for a tag (type, chapter, section, book_id)
"""

import re
from html.parser import HTMLParser
from typing import Optional
import requests
from fastmcp import FastMCP

BASE = "https://stacks.math.columbia.edu"
mcp = FastMCP(
    "stacks",
    instructions=(
        "Query the Stacks Project (stacks.math.columbia.edu) — the open-source "
        "algebraic geometry and commutative algebra reference. "
        "Use get_tag to fetch a known tag's statement, search_stacks to find tags "
        "by keyword, and tag_info for location metadata."
    ),
)


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

class _StripHTML(HTMLParser):
    """Strip HTML tags; preserve text content (which contains raw LaTeX)."""

    SKIP = {"script", "style"}
    NEWLINE_ON = {"p", "br", "div", "article"}

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in self.SKIP:
            self._skip += 1
        elif tag in self.NEWLINE_ON:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP:
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._parts.append(data)

    def text(self) -> str:
        raw = "".join(self._parts)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def _html_to_text(html: str) -> str:
    p = _StripHTML()
    p.feed(html)
    return p.text()


def _get(url: str, timeout: int = 10) -> Optional[requests.Response]:
    try:
        r = requests.get(url, timeout=timeout)
        return r if r.status_code == 200 else None
    except requests.RequestException:
        return None


def _extract_tag_hierarchy(html: str) -> dict:
    """Extract chapter/section hierarchy from a tag page's link context."""
    # Links adjacent to ': Name' are breadcrumb entries:
    # e.g. '10.103</a>: Cohen-Macaulay modules' → section 10.103
    hierarchy: dict = {}
    for tag, text, after in re.findall(
        r'href="/tag/([A-Z0-9]{4})"[^>]*>([^<]+)</a>([^<]{0,120})',
        html,
    ):
        after = after.strip()
        if after.startswith(":"):
            name = after[1:].strip()
            # chapter = single integer (e.g. "10"), section = "X.Y"
            if re.fullmatch(r"\d+", text.strip()):
                hierarchy["chapter"] = f"Chapter {text.strip()}: {name}"
                hierarchy["chapter_tag"] = tag
            elif re.fullmatch(r"\d+\.\d+", text.strip()):
                hierarchy["section"] = f"Section {text.strip()}: {name}"
                hierarchy["section_tag"] = tag
    return hierarchy


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool
def get_tag(tag: str, include_proof: bool = False) -> str:
    """Fetch the statement (and optionally proof) of a Stacks Project tag.

    Args:
        tag: 4-character tag identifier, e.g. "00N3" (Cohen-Macaulay definition)
             or "00XY" (lemma on morphisms of sites).
        include_proof: Return the proof as well (default False).

    Returns:
        LaTeX-rich text of the statement (and proof when requested).
        Math appears inline as $...$ or display as \\[...\\] / \\begin{...}...\\end{...}.
    """
    tag = tag.upper().strip()
    endpoint = "full" if include_proof else "statement"
    url = f"{BASE}/data/tag/{tag}/content/{endpoint}"
    r = _get(url)
    if r is None:
        return f"Tag {tag!r} not found or network error."
    text = _html_to_text(r.text)
    if not text or "Not Found" in text:
        return f"Tag {tag!r} not found."
    return text


@mcp.tool
def tag_info(tag: str) -> str:
    """Return metadata for a Stacks Project tag: type, book_id, chapter, section.

    Args:
        tag: 4-character tag identifier (case-insensitive).

    Returns:
        Metadata including tag type (lemma/definition/theorem/…),
        book_id (e.g. "10.103.1"), chapter, and section location.
    """
    tag = tag.upper().strip()
    url = f"{BASE}/tag/{tag}"
    r = _get(url)
    if r is None:
        return f"Tag {tag!r} not found or network error."
    html = r.text

    # Type and book_id from <title>
    title_m = re.search(r"<title>([^&(]+)\s*\([A-Z0-9]{4}\)", html)
    label = title_m.group(1).strip() if title_m else ""
    # label is like "Definition 10.103.1"
    type_m = re.match(r"(\w+)\s+([\d.]+)", label)
    env_type = type_m.group(1).lower() if type_m else "unknown"
    book_id = type_m.group(2) if type_m else ""

    hier = _extract_tag_hierarchy(html)

    lines = [
        f"tag: {tag}",
        f"type: {env_type}",
        f"book_id: {book_id}",
        f"chapter: {hier.get('chapter', '')}",
        f"section: {hier.get('section', '')}",
        f"url: {BASE}/tag/{tag}",
    ]
    return "\n".join(lines)


@mcp.tool
def search_stacks(query: str, max_results: int = 20) -> str:
    """Search the Stacks Project by keyword.

    Supports SQLite FTS wildcards: "ideal*" matches "ideals"; quote multi-word
    strings: '"quasi-compact"' to avoid treating '-' as NOT.

    Args:
        query: Search keywords, e.g. "Cohen-Macaulay", "flat module*",
               '"locally Noetherian"'.
        max_results: Maximum number of results to return (default 20).

    Returns:
        Newline-separated results, each with tag, type, book_id, and a
        LaTeX preview snippet (first ~200 chars of statement).
    """
    url = f"{BASE}/search?query={requests.utils.quote(query)}"
    r = _get(url, timeout=20)
    if r is None:
        return f"Search request failed for {query!r}."

    html = r.text

    # Total count
    count_m = re.search(r"(\d+)\s+results?", html)
    total = int(count_m.group(1)) if count_m else 0

    if total == 0:
        return f"No results for {query!r}."

    # Extract leaf result items: only <li> that directly contain an <article>
    # (not chapter/section grouping nodes).
    # Strategy: find all <article class="env-TYPE" id="TAG"> elements, then
    # extract the surrounding preview-title for context.
    results = []
    for art_m in re.finditer(
        r'<article\s+class="env-(\w+)"\s+id="([A-Z0-9]{4})"[^>]*>(.*?)</article>',
        html,
        re.DOTALL,
    ):
        if len(results) >= max_results:
            break
        env_type = art_m.group(1)
        item_tag = art_m.group(2)
        art_html = art_m.group(3)

        # Extract LaTeX text from the article
        preview = _html_to_text(art_html)
        preview = " ".join(preview.split())[:200]

        # Find the preview-title just before this article for book_id
        # Search backwards in html for the nearest preview-title
        start = art_m.start()
        preceding = html[max(0, start - 600):start]
        title_m = re.search(
            r'class="preview-title">(.*?)(?=</span>)',
            preceding,
            re.DOTALL,
        )
        title = _html_to_text(title_m.group(1)).strip() if title_m else ""

        results.append(
            f"[{item_tag}] {env_type}: {title}\n  {preview}"
        )

    if not results:
        return f"Search returned {total} results but could not parse items for {query!r}."

    header = f"{total} results for {query!r} (showing {len(results)}):\n\n"
    return header + "\n\n".join(results)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
