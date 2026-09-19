root <- "C:/Users/pgoff/Mentat/mentat"
for (f in c("paths.R", "schema.R", "ingest.R", "collect.R", "fec_api.R")) source(file.path(root, "R", f))
Sys.unsetenv("MENTAT_REQUEST_POOL_WIDTH")
unit <- list(id="audit-window-drift", company="Audit", cycle=2026L, kind="employer",
  phase="P1_employer", variants="AUDIT", company_variants="AUDIT", industry="Audit",
  query_field="contributor_employer", query_filters=list())
calls <- 0L
transport <- function(specs, api_key, concurrency) lapply(specs, function(spec) {
  calls <<- calls + 1L
  if (!grepl("::window::",spec$id,fixed=TRUE)) {
    if (!is.null(spec$params$last_index)) return(list(status=504L,body="",elapsed_seconds=0.01))
    return(list(status=200L,json=list(results=list(list(sub_id="observed-1")),
      pagination=list(is_count_exact=TRUE,count=3L,last_indexes=list(last_index="next",last_contribution_receipt_date="2026-01-01")))))
  }
  rows <- if (endsWith(spec$id,"::01")) list(list(sub_id="observed-1"),list(sub_id="observed-2")) else list()
  list(status=200L,json=list(results=rows,pagination=list(is_count_exact=TRUE,count=length(rows),last_indexes=list())))
})
result <- fec_api_collect_work_units(list(unit), api_key="synthetic", concurrency=4L,
  transport=transport,sleep=function(...)NULL,jitter=function(...)0)
state <- result$units[[unit$id]]
cat(sprintf("Original exact count=3; window union=%d; complete=%s; coverage_verified=%s; requests=%d\n",
  state$expected_count,state$complete,state$coverage_verified,calls))
stopifnot(state$expected_count==2L,state$complete,isTRUE(state$coverage_verified))
