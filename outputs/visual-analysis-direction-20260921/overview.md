# Mentat: compare giving, then trace it to evidence

Proposed direction for Graph, PAC evidence, and Insights. Generated with Higgsfield on September 21, 2026. These are coordinated screen concepts, not implemented screenshots. All illustrated financial data is synthetic.

| Workspace | Main visual | Evidence interaction |
| --- | --- | --- |
| Graph | Large ranked horizontal giving comparison | Select a recipient, inspect exact records, open compatible PAC evidence |
| PAC evidence | Geographic distribution linked to ranked bars | Select a place, inspect activity and filing records; keep unlocated amounts visible |
| Insights | Large trend comparison with recipient and change analyses below | Inspect values and underlying records for each comparison |

The earlier pass standardized CSS but retained competing information layouts. This proposal gives all three workspaces the same shell, scope band, analysis navigation, chart actions, and evidence behavior, while reserving most of the content area for readable visual analysis.

## Graph

![Proposed Graph mockup](https://d8j0ntlcm91z4.cloudfront.net/user_3J1aVESwhbXLraSW8PtRFWWgpV2/hf_20260921_142126_e50a039b-85a1-4ef8-9ad1-b14b327933fc.png)

## PAC evidence

![Proposed PAC evidence mockup](https://d8j0ntlcm91z4.cloudfront.net/user_3J1aVESwhbXLraSW8PtRFWWgpV2/hf_20260921_142127_9f2289b3-75a0-4df9-abe9-908ae7e7180e.png)

## Insights

![Proposed Insights mockup](https://d8j0ntlcm91z4.cloudfront.net/user_3J1aVESwhbXLraSW8PtRFWWgpV2/hf_20260921_142126_45b09094-e866-4602-b792-0c913bcbdfb3.png)

## Review before implementation

The mockups establish composition. The implementation prompt resolves their generated inconsistencies: common underline analysis navigation, common chart toggles, no Chart control on a records panel, actual source metadata instead of the invented accrual label, real geographic boundaries, and current cycle-level Insights data instead of unsupported monthly interpolation.

The primary decision is whether to carry forward this chart-first composition and shared evidence-detail behavior, or revise the chart/rail proportions and density.

Read the companion [implementation prompt](./implementation-prompt.md). Exact generation prompts and job IDs are preserved in [generation-prompts.json](./generation-prompts.json).

