# Project principles — CHDK A590 IS Ukrainian Edition

Target: Canon PowerShot A590 IS firmware GM1.01B.

## Primary objective

Maximize achievable photographic quality, camera capabilities, responsiveness, and Ukrainian-language usability while preserving original Canon functionality and CHDK compatibility.

**Power efficiency is not an optimization goal.** Additional CPU time or RAM use is acceptable when justified by a demonstrated improvement and when hardware safety and stability margins are preserved.

## Non-negotiable invariants

1. Do not write to internal camera firmware/flash as part of ordinary development or deployment.
2. Keep an unmodified, reproducibly built baseline for A590 IS 1.01B and a reversible SD-card rollback procedure.
3. Preserve normal Canon shooting, playback, autofocus, optical stabilization, flash, and file saving; preserve existing CHDK functionality.
4. Avoid unbounded allocations, unsafe memory access, stack exhaustion, task starvation, or blocking time-critical firmware paths.
5. Do not assert that features are reliable or that picture quality is improved without measurement and physical camera testing.
6. Never use firmware-specific boot patches for a mismatched firmware revision.

## Performance philosophy

- Use available CPU cycles when they materially improve output.
- Spend RAM intelligently, reserving measured headroom for Canon firmware and image capture.
- Prefer optimized native algorithms for latency-sensitive workloads, scripts for experimentation, and offline post-processing when on-camera resource limits make it better.
- Measure baseline and modified behavior: free memory, code size, response time, capture latency, RAW integrity, error rates, and image quality.
- Do not compromise safety for benchmark gains.

## Candidate improvements — investigate feasibility first

1. Exposure metering and highlight-preserving exposure logic.
2. Intelligent exposure bracketing and automated HDR capture sequences.
3. RAW/DNG workflow and metadata correctness.
4. Focus bracketing and repeatable timed shooting.
5. Better UX: clear Ukrainian menus, quick controls, restrained screen drawing.
6. Optional computational methods only if benchmarks show feasibility on DIGIC III; otherwise provide an offline pipeline.

Features may be proposed, prototyped, and benchmarked independently. Do not assume access to proprietary internal ISP algorithms, or promise changes to Canon's AWB/NR/AF without verified hooks.

## Release gate

Every feature needs documented expected gain, CPU/RAM budget, regression tests, a way to disable or roll it back, and real-world camera validation before release.
