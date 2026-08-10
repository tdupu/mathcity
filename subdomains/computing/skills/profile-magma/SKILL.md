---
name: profile-magma
description: Wrap the Magma code the user is working on in a profiling harness to find bottlenecks (slow intrinsics, memory hogs). Trigger when a Magma computation is "slow", "eating memory", "hanging", or "timing out", when the user asks "what's slow here?", "can we profile this?", "which intrinsic is the bottleneck?", or after killing a Magma process to diagnose before rerunning. Do NOT trigger for general Magma scripting help — only performance diagnosis.
---

# profile-magma

Wrap the Magma code the user is currently working on in a profiling harness
to identify bottlenecks (slow intrinsics, memory hogs).

## When to trigger

Use this skill when the user:
- Says a Magma computation is "slow", "eating memory", "hanging", or "timing out"
- Wants to know which intrinsic is the bottleneck
- Asks "what's slow here?", "can we profile this?", "what's taking so long?"
- Has just killed a Magma process and wants to diagnose before rerunning

Do NOT trigger for general Magma scripting help; only when the goal is performance diagnosis.

## What this skill does

1. Identifies the suspect code from context (the computation the user was running).
2. Creates a minimal probe `.mag` file in `magma/test/` named `probe-profile-<topic>.mag`.
3. The probe wraps the suspect calls in Magma's built-in profiler:
   ```magma
   SetProfile(true);
   // ... suspect code ...
   SetProfile(false);
   ProfilePrintByTotalTime(:Max := 20);
   ```
4. Runs the probe and reports the top-20 intrinsics by total time.
5. Optionally repeats with a smaller/simpler input to isolate the bottleneck
   without blowing up memory.

## Magma profiler API

```magma
SetProfile(true);            // start recording
// ... code to profile ...
SetProfile(false);           // stop recording
ProfilePrintByTotalTime(:Max := N);   // print top N by total CPU time
```

`ProfilePrintByTotalTime` prints a table: intrinsic name, call count, total
time, self time. "Self time" (time inside the intrinsic, not in callees) is
the sharpest signal for where actual work happens.

There is no built-in memory profiler in Magma. For memory diagnosis, use
`GetMemoryUsage()` before and after suspect calls:

```magma
m0 := GetMemoryUsage();
// ... suspect call ...
m1 := GetMemoryUsage();
printf "Delta memory: %o MB\n", (m1 - m0) div (1024*1024);
```

## Probe file template

```magma
/*
probe-profile-<topic>.mag — Profile <topic> to identify bottleneck.
Run from magma/test/:  magma probe-profile-<topic>.mag
*/
SetColumns(0);
Z := Integers(); Q := Rationals();
AttachSpec("../hecke.spec");
SetLMFDBRootFolder("../");
SetVerbose("Clifford", 0);

T0 := Cputime();
// --- minimal setup (just enough to reach the suspect call) ---
// ...

m0 := GetMemoryUsage();
SetProfile(true);

// --- suspect code ---
// ...

SetProfile(false);
m1 := GetMemoryUsage();
printf "CPU: %.2os   Memory delta: %o MB\n",
    Cputime(T0), (m1-m0) div (1024*1024);
printf "\n=== Profile (top 20 by total time) ===\n";
ProfilePrintByTotalTime(:Max := 20);
quit;
```

## Strategy

- **Start small**: use the simplest input (smallest index subgroup, lowest
  prime) to get a readable profile without running out of memory.
- **Bisect**: if the top entry is an unfamiliar built-in (e.g. `AbelianQuotient`,
  `quo<>`, `hom<>`), wrap just that call in a second probe and confirm it's
  the culprit before looking for fixes.
- **Memory vs time**: a slow call and a memory-eating call are often different.
  Profile CPU first (via `ProfilePrintByTotalTime`), then add `GetMemoryUsage`
  deltas around the top offender.
- **Check what's stored**: if the bottleneck recomputes something already in
  the LMFDB data (abelianization, generators, coset reps), propose reading
  from the stored fields instead of recomputing.

## Output interpretation

After running `ProfilePrintByTotalTime`, look for:

| Signal | Meaning |
|---|---|
| High *self* time on a built-in like `AbelianQuotient`, `quo<>`, `SmithNormalForm` | The group/module computation itself is expensive |
| High *self* time on `fp_element_to_matrix` or `matrix_to_fp_element` | Word evaluation in a large FP group is the bottleneck |
| High *self* time on a BFS/traversal (`right_transversal_matrices`) | The subgroup index is too large for the fast path |
| High *total* but low *self* on a wrapper | The wrapper is fine; dig into its callees |
| Memory OOM before profile prints | Reduce input size; add `GetMemoryUsage` checkpoints |

## Working directory

Always run probes from `magma/test/` — that's where `AttachSpec("../hecke.spec")`
and `SetLMFDBRootFolder("../")` resolve correctly.
