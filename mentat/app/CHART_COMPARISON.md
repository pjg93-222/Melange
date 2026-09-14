# Comparing charts

Use the **1 chart / 2 charts / 3 charts / 4 charts** buttons in Chart Studio. Four charts use a two-by-two grid; narrow screens stack them. Reducing the count hides the extra charts and preserves their settings. Each chart keeps its own sheets, source, accounting basis, chart variant, filters, query results, inspection state, and downloads.

**Hide all options** creates a comparison view. **Show options** on a chart reopens its editor. The Chart variant selector uses the existing supported chart families; field requirements still apply to each variant.

Open **Linked filters** to link Company, Party, Contributor state, Recipient committee state, or Candidate represented state. Company is linked initially. Turning a link on copies Chart A's filter to the other visible charts; later changes in any visible chart propagate that selected filter. Cycles and unselected filters remain independent. Unsupported fields are reported, not substituted. Each chart uses its own axis scale.

# State destinations

Under Data, choose a **State location view**. Recipient committee address, candidate represented state, and contributor state are separate fields. The first two require a freshly generated workbook with destination schema 1. Older workbooks display a regeneration message.

Workbook generation adds **State Destinations** and **Recipient Locations** sheets. Destination totals cover all included receipts and reconcile independently to the same population. Never add the two location partitions together. Candidate mapping uses cycle-specific principal/authorized committee links. Multiple candidates remain ambiguous, missing links remain unknown, and presidential candidates are national. Committee locations retain DC, territories, and unrecognized reported codes separately.

Candidate geography does not trace later committee spending or allocate one company's money across beneficiaries. Existing Downstream Activity remains a separate accounting stage. The compact workbook payload retains location and evidence fields for verified contribution queries.

Restart Mentat after installing code changes. Regenerate existing published workbooks through the normal guarded report pipeline to populate destination fields; editing workbook cells by hand cannot supply verified source lineage.
