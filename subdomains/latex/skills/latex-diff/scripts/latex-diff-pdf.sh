#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: $0 OLD.tex NEW.tex OUTPUT_DIR [BASENAME]" >&2
  exit 2
}

[[ $# -ge 3 && $# -le 4 ]] || usage

old_input=$1
new_input=$2
output_dir=$3
base_name=${4:-latex-diff}

command -v latexdiff >/dev/null 2>&1 || {
  echo "latex-diff-pdf: latexdiff is required" >&2
  exit 1
}
command -v latexmk >/dev/null 2>&1 || {
  echo "latex-diff-pdf: latexmk is required" >&2
  exit 1
}

old_dir=$(cd "$(dirname "$old_input")" && pwd -P)
new_dir=$(cd "$(dirname "$new_input")" && pwd -P)
old_file=$old_dir/$(basename "$old_input")
new_file=$new_dir/$(basename "$new_input")

[[ -f "$old_file" && -f "$new_file" ]] || {
  echo "latex-diff-pdf: both inputs must be regular files" >&2
  exit 1
}

mkdir -p "$output_dir"
output_dir=$(cd "$output_dir" && pwd -P)
diff_tex=$output_dir/$base_name.tex
diff_pdf=$output_dir/$base_name.pdf
build_dir=$(mktemp -d "$output_dir/.latex-diff-build.XXXXXX")
legacy_defs=$(mktemp "$build_dir/legacy-defs.XXXXXX")
trap 'rm -rf "$build_dir"' EXIT

latexdiff --type=UNDERLINE --graphics-markup=none --flatten \
  "$old_file" "$new_file" > "$diff_tex"

[[ -s "$diff_tex" ]] || {
  echo "latex-diff-pdf: latexdiff produced an empty source" >&2
  exit 1
}
grep -q '\\DIFadd' "$diff_tex" || grep -q '\\DIFdel' "$diff_tex" || {
  if cmp -s "$old_file" "$new_file"; then
    echo "latex-diff-pdf: inputs are identical; no diff was created" >&2
    exit 0
  fi
  echo "latex-diff-pdf: differing inputs have no DIF markup" >&2
  exit 1
}
grep -q '\\color{blue}' "$diff_tex" || {
  echo "latex-diff-pdf: blue addition markup is missing" >&2
  exit 1
}
grep -q '\\color{red}' "$diff_tex" || {
  echo "latex-diff-pdf: red deletion markup is missing" >&2
  exit 1
}

# Keep old-only macro definitions available to deleted text.  latexdiff quite
# correctly marks a removed definition as deleted, but TeX still needs the
# macro to parse the deleted material.  Restrict this compatibility block to
# one-line preamble definitions that are absent from the new source.
perl -ne '
  last if index($_, "\x5c" . "begin{document}") >= 0;
  print if m{\x5c(?:newcommand|renewcommand|DeclareMathOperator)\*?\s*\{\x5c[A-Za-z@]+\}};
' "$old_file" > "$legacy_defs"
legacy_compat="$build_dir/legacy-compat.tex"
: > "$legacy_compat"
while IFS= read -r definition; do
  macro=$(printf '%s\n' "$definition" | perl -ne \
    'if (m{\x5c(?:newcommand|renewcommand|DeclareMathOperator)\*?\s*\{\x5c([A-Za-z@]+)\}}) { print $1 }')
  [[ -n "$macro" ]] || continue
  if ! grep -Eq "\\\\(newcommand|renewcommand|DeclareMathOperator)\\*?[[:space:]]*\\{\\\\$macro\\}" "$new_file"; then
    printf '%s\n' "$definition" >> "$legacy_compat"
  fi
done < "$legacy_defs"
if [[ -s "$legacy_compat" ]]; then
  awk -v compat="$legacy_compat" -v begin_document='\\begin{document}' '
    index($0, begin_document) && !inserted {
      print "% Legacy definitions retained for deleted material."
      while ((getline line < compat) > 0) print line
      close(compat)
      inserted=1
    }
    { print }
  ' "$diff_tex" > "$diff_tex.tmp"
  mv -f "$diff_tex.tmp" "$diff_tex"
fi

TEXINPUTS="$new_dir:$old_dir:${TEXINPUTS:-}" \
BIBINPUTS="$new_dir:$old_dir:${BIBINPUTS:-}" \
latexmk -pdf -interaction=nonstopmode -halt-on-error \
  -outdir="$build_dir" "$diff_tex"

[[ -s "$build_dir/$base_name.pdf" ]] || {
  echo "latex-diff-pdf: latexmk produced no PDF" >&2
  exit 1
}
cp -f "$build_dir/$base_name.pdf" "$diff_pdf"
echo "$diff_pdf"
