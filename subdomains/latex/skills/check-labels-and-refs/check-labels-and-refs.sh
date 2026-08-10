#!/bin/bash
set -euo pipefail

# check-labels-and-refs — Scan LaTeX files for label/reference consistency
# Usage: check-labels-and-refs <tex-file> [output-dir] [bead-id]

ROOT_TEX="${1:?Missing root TeX file}"
OUTPUT_DIR="${2:-$HOME/gt/tmp-for-review/}"
WORK_BEAD_ID="${3:-he-ja26}"

if [[ ! -f "$ROOT_TEX" ]]; then
  echo "ERROR: Root TeX file not found: $ROOT_TEX" >&2
  exit 1
fi

REPORT_DIR="${OUTPUT_DIR}/${WORK_BEAD_ID}"
mkdir -p "$REPORT_DIR"

python3 << 'EOF'
import json
import re
import os
import sys
import subprocess
from pathlib import Path
from collections import defaultdict

root_tex = os.environ.get('ROOT_TEX')
report_dir = os.environ.get('REPORT_DIR')

if not root_tex or not report_dir:
    sys.exit(1)

root_dir = os.path.dirname(root_tex)

# Collect all .tex files via \input/\include closure (depth <= 2)
files_to_scan = {root_tex}
queue = [root_tex]
depth = 0

while queue and depth < 2:
    depth += 1
    new_queue = []
    for file in queue:
        try:
            with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                # Find \input and \include patterns
                for match in re.finditer(r'\\(?:input|include)\{([^}]+)\}', content):
                    inc_path = match.group(1)
                    if not inc_path.endswith('.tex'):
                        inc_path += '.tex'
                    full_path = os.path.join(os.path.dirname(file), inc_path)
                    if os.path.exists(full_path):
                        full_path = os.path.abspath(full_path)
                        if full_path not in files_to_scan:
                            files_to_scan.add(full_path)
                            new_queue.append(full_path)
        except:
            pass
    queue = new_queue

# Collect labels and references
labels = {}  # label_name -> {location, referenced_from: []}
refs = defaultdict(lambda: {'locations': [], 'label_found': False, 'reference_type': 'ref'})

for file in sorted(files_to_scan):
    try:
        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                # Find labels: \label{<name>}
                for match in re.finditer(r'\\label\{([^}]+)\}', line):
                    label_name = match.group(1)
                    labels[label_name] = {'location': f"{file}:{line_num}", 'referenced_from': []}

                # Find references: \ref{}, \eqref{}, \autoref{}, etc.
                for match in re.finditer(r'\\(\w*ref)\{([^}]+)\}', line):
                    ref_type = match.group(1) or 'ref'
                    ref_name = match.group(2)
                    refs[ref_name]['locations'].append(f"{file}:{line_num}")
                    refs[ref_name]['reference_type'] = ref_type
    except:
        pass

# Cross-reference: update references with label_found flag and referenced_from lists
for ref_name in refs:
    if ref_name in labels:
        refs[ref_name]['label_found'] = True
        for loc in refs[ref_name]['locations']:
            labels[ref_name]['referenced_from'].append(loc)

# Detect non-pinpoint references (simple example patterns)
non_pinpoint = []
# v0 ships with single example pattern
patterns = [
    (r'(?i)section\s+\d+(?![.\-\d])', 'bare-section'),
]

for file in sorted(files_to_scan):
    try:
        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                for pattern, ptype in patterns:
                    # Only flag if not already in a \ref command
                    if re.search(pattern, line) and not re.search(r'\\[a-z]*ref', line):
                        non_pinpoint.append({
                            'file': file,
                            'line': line_num,
                            'context': line.strip()[:100],
                            'pattern': ptype
                        })
                        break  # Avoid duplicate entries
    except:
        pass

# Get git SHA
try:
    sha = subprocess.check_output(
        ['git', '-C', root_dir, 'rev-parse', 'HEAD'],
        stderr=subprocess.DEVNULL
    ).decode().strip()[:7]
except:
    sha = 'unknown'

# Compute verdict
orphan_labels = [name for name, data in labels.items() if not data['referenced_from']]
orphan_refs = [name for name, data in refs.items() if not data['label_found']]
verdict = 'PASS' if (not orphan_labels and not orphan_refs and not non_pinpoint) else 'FAIL'

# Build report
report = {
    'file': root_tex,
    'sha': sha,
    'scan_depth': 2,
    'verdict': verdict,
    'labels': {
        name: {'location': data['location'], 'referenced_from': data['referenced_from']}
        for name, data in sorted(labels.items())
    },
    'references': dict(sorted({
        name: {
            'locations': data['locations'],
            'label_found': data['label_found'],
            'reference_type': data['reference_type']
        }
        for name, data in refs.items()
    }.items())),
    'orphan_labels': sorted(orphan_labels),
    'orphan_refs': sorted(orphan_refs),
    'non_pinpoint_refs': non_pinpoint,
    'counts': {
        'total_labels': len(labels),
        'total_refs': len(refs),
        'orphan_label_count': len(orphan_labels),
        'orphan_ref_count': len(orphan_refs),
        'non_pinpoint_count': len(non_pinpoint),
    }
}

# Write report
report_path = os.path.join(report_dir, 'check-labels-and-refs-report.json')
os.makedirs(report_dir, exist_ok=True)
with open(report_path, 'w') as f:
    json.dump(report, f, indent=2)

# Output to stdout
print(json.dumps(report, indent=2))
EOF
