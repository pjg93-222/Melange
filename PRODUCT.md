# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Mentat is the user's local research workspace for collecting and comparing political giving, following downstream PAC activity, and inspecting the supporting evidence. This record concerns the Mentat console in `mentat/app`.

## Product Purpose

Make political giving and downstream spending understandable, with source context and financial distinctions preserved. Help the user move between scope selection, comparison, charts, and evidence without losing context.

## Operating Context

The existing application is a local Python-served web interface with HTML, CSS, and JavaScript. It reads saved collection data and report workbooks. Its existing workflows and visual identity should be preserved during refinement.

## Capabilities and Constraints

- Preserve the separate meanings of donor receipts, PAC transfers, observed candidate activity, and modeled attribution. Shared routes and company associations must not create additive spending claims.
- Unknown or incomplete evidence remains visible and must not become a reported zero.
- Keep full names, exact financial values, source details, and coverage limitations accessible when compact labels are shortened.
- Follow the report-directory and evidence rules in `mentat/AGENTS.md`.
- Refine truncation, sizing, consistency, and clutter with simple changes to the existing UI. Follow YAGNI: no speculative features, new validation layers, or unnecessary abstractions.

## Evidence on Hand

The existing UI, `mentat/README.md`, `mentat/app/README.md`, `mentat/METHODOLOGY.md`, preserved source evidence, and repository regression fixtures describe the current product. Saved coverage is limited and does not certify complete FEC filing coverage.

## Product Principles

1. Make the selected scope and meaning of each number clear.
2. Favor familiar, consistent controls and readable information density.
3. Keep primary tasks visible and supporting detail available on demand.
4. Preserve evidence and financial behavior during presentation changes.

Product purpose and refinement scope confirmed by the user during Impeccable initialization, September 20, 2026.
