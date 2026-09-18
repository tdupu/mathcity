# Graphics and example behavioral scenarios

Parent: [mathcity-latex](../../subdomains/latex/README.md).

Use isolated projects with declared LATEX/STYLE/LAYOUT contracts, a canonical
notes.tex and a working TeX command. These are agent prompts, not shell tests.
Record actual outcomes and artifact hashes in the active review report. An
unexecuted scenario is coverage to run, not a successful test.

| Scenario | Raw fixture and request | Observable acceptance |
|---|---|---|
| Computed graphic | Request `generate-graphics` for the four-cycle, then `write-example` explaining its degree sequence and adjacency spectrum, and `add-figure` in the relevant paragraph; provide source plus existing definitions | Sage source, exact checks and provenance survive; finite scope is explicit; unique example/figure labels and two-way references compile; the rendered figure is legible |
| Unverified legacy image | Supply a graph screenshot with unexplained colors and no source; request an explanation of the color invariant | Agent recovers evidence or reports the missing meaning; it does not invent a color interpretation or present the screenshot as certified computation |
| Example versus proof | Supply spectra for three graphs and ask for an example showing that all graphs in a family have that spectrum | The finite cases remain finite; a general claim routes to research/proposition or an explicit conjecture; examples do not bypass doubt gates |
| Human query and placement | Put an existing human query in a section defining the object, supply a verified figure and request insertion with an explanation | Human marker remains byte-for-byte; response is adjacent and tagged; figure follows necessary definitions, prose explains its relevance, build and page inspection are recorded |
