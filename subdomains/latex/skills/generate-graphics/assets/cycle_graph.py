"""Runnable Sage graphics template: a checked finite graph, not research data.

Run: sage -python cycle_graph.py <new-output-dir>
The destination must not exist, so reruns cannot overwrite curated figures.
Adapt the construction, assertions, and provenance together for real work.
"""

import hashlib
import json
from pathlib import Path
import platform
import sys

import matplotlib
from sage.all import ZZ, graphs
from sage.env import SAGE_VERSION


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: sage -python cycle_graph.py <new-output-dir>")
    destination = Path(sys.argv[1])
    if destination.exists():
        raise SystemExit("Output directory already exists; choose a new directory.")

    graph = graphs.CycleGraph(4)
    vertices = list(range(4))
    adjacency = graph.adjacency_matrix(vertices=vertices)
    characteristic = adjacency.charpoly()
    polynomial_ring = characteristic.parent()
    x = polynomial_ring.gen()
    expected_characteristic = x**2 * (x**2 - 4)
    spectrum = sorted(int(value) for value in adjacency.eigenvalues())
    degrees = sorted(int(value) for value in graph.degree())
    edges = sorted(sorted([int(u), int(v)]) for u, v in graph.edges(labels=False))
    assert graph.order() == 4 and graph.size() == 4
    assert degrees == [2, 2, 2, 2]
    assert sum(degrees) == 2 * graph.size()
    assert characteristic == expected_characteristic
    assert spectrum == [-2, 0, 0, 2]
    assert sum(spectrum) == adjacency.trace() == 0
    assert sum(value**2 for value in spectrum) == 2 * graph.size()

    # Layout is illustrative; all topology comes from the computed graph.
    positions = {0: (1, 0), 1: (0, 1), 2: (-1, 0), 3: (0, -1)}
    graphic = graph.plot(
        pos=positions,
        vertex_labels=True,
        vertex_colors={"#0072B2": vertices},
        vertex_size=450,
        edge_color="#444444",
        edge_thickness=2,
        axes=False,
    )
    destination.mkdir(parents=True, exist_ok=False)
    pdf = destination / "cycle-graph.pdf"
    png = destination / "cycle-graph.png"
    graphic.save(str(pdf), figsize=[4, 4], axes=False)
    graphic.save(str(png), figsize=[4, 4], dpi=180, axes=False)

    source = Path(__file__)
    (destination / source.name).write_bytes(source.read_bytes())
    manifest = {
        "figure_id": "cycle-graph",
        "purpose": "Illustrate one exact four-cycle with labelled vertices.",
        "evidence_kind": "exact-computation",
        "source": {"path": source.name, "sha256": sha256(source)},
        "inputs": {"inline": {"construction": "graphs.CycleGraph(4)", "order": 4}},
        "reproduce": {
            "working_directory": "Manifest directory (contains an exact source copy)",
            "argv": ["sage", "-python", source.name, "<new-output-dir>"],
            "dependencies": ["SageMath with matplotlib"],
            "path_convention": "All file paths relative to the manifest directory",
        },
        "software": {
            "sage": SAGE_VERSION,
            "python": platform.python_version(),
            "matplotlib": matplotlib.__version__,
        },
        "randomness": {"seed": None, "reason": "No sampling; fixed graph and explicit vertex positions"},
        "arithmetic": {"ring": str(ZZ), "precision": None, "tolerance": None, "reason": "Exact integer adjacency and characteristic polynomial"},
        "semantics": {
            "vertices": "Integers 0 through 3; all have the same mathematical role",
            "edges": "Undirected simple unweighted graph, no loops or parallel edges",
            "operator": "Unnormalized adjacency in vertex order [0, 1, 2, 3]",
            "colors": {"#0072B2": "Every vertex", "#444444": "Every edge"},
            "positions": positions,
            "layout": "Illustrative embedding only; coordinate distances have no invariant meaning",
        },
        "scope": "Complete single finite graph; no sampling, filtering, quotienting, or omitted vertices",
        "computed": {
            "adjacency": [[int(entry) for entry in row] for row in adjacency.rows()],
            "edges": edges,
            "degrees": degrees,
            "characteristic_polynomial": str(characteristic),
            "spectrum_with_multiplicity": spectrum,
        },
        "checks": [
            {"description": "Vertex and edge counts", "expected": [4, 4], "observed": [int(graph.order()), int(graph.size())], "passed": True},
            {"description": "Degree sum equals twice the edge count", "expected": 8, "observed": sum(degrees), "passed": True},
            {"description": "Characteristic polynomial", "expected": str(expected_characteristic), "observed": str(characteristic), "passed": True},
            {"description": "Spectrum including multiplicities", "expected": [-2, 0, 0, 2], "observed": spectrum, "passed": True},
            {"description": "Eigenvalue sum equals adjacency trace", "expected": 0, "observed": sum(spectrum), "passed": True},
            {"description": "Sum of squared eigenvalues equals twice the edge count", "expected": 8, "observed": sum(value**2 for value in spectrum), "passed": True},
        ],
        "artifacts": [
            {"path": pdf.name, "format": "application/pdf", "sha256": sha256(pdf)},
            {"path": png.name, "format": "image/png", "sha256": sha256(png)},
        ],
        "limitations": ["Only this four-cycle was computed; no general graph theorem follows from the picture."],
        "render_review": {"status": "pending", "reason": "Script checks data but cannot inspect the rendered image"},
    }
    (destination / "cycle-graph.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print("Created cycle_graph.py, cycle-graph.pdf, cycle-graph.png, and cycle-graph.json")


if __name__ == "__main__":
    main()
