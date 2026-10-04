# Citing mathcity skills in a manuscript

For an author whose paper used a mathcity skill (`using-latexpowers`,
`referee-report`, `frontier-dump`, …) and needs a citation that a
reader can follow. The rules a manuscript must meet are the repository's
own `AI-POLICY.md`; this note shows how mathcity skills satisfy its
software-citation and workflow-citation rules (AI2, AI3 in the template
at `subdomains/repo-docs/templates/AI-POLICY.md`).

## The citation

Cite the repository once, pinned to the commit that was actually run, and
give the skill's path as the pinpoint at each use.

```bibtex
@misc{Mathcity26,
  author = {Dupuy, Taylor},
  title  = {mathcity: skills and policies for mathematical research with
            {AI} agents},
  year   = {2026},
  url    = {https://github.com/tdupu/mathcity/tree/<commit>},
  note   = {Commit <commit>}
}
```

```latex
The draft was reviewed with the \texttt{referee-report} skill
\cite[\texttt{subdomains/latex/skills/referee-report}]{Mathcity26}.
```

If one paper used skills at several commits, give one entry per commit.

## Which commit

Take the commit from the run's provenance record (`ai/ai-usage.md` in the
manuscript's repository, written by `update-ai-usage`), never from the
current `HEAD`: the skill may have changed since the run. If the record
does not name a commit, say so in the disclosure rather than guessing.
To find which repository holds an installed skill, use
`readlink -f ~/.claude/skills/<name>`.

A commit is citable only once it is on the public `origin/main`. Check with
`git branch -r --contains <commit>` before citing.

## Mirrored skills

Some skills are maintained in another repository and mirrored here so they
can be cited publicly; [agent-skills-mirror.md](agent-skills-mirror.md)
lists each one with the source commit it was mirrored from. Cite the
mathcity commit that contains the mirror, and record the source commit in
the provenance record.
