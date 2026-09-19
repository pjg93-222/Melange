args <- commandArgs(trailingOnly = FALSE)
root <- "C:/Users/pgoff/Mentat/mentat"
for (f in c("paths.R","schema.R","ingest.R","collect.R","fec_api.R")) source(file.path(root,"R",f))
Sys.setenv(MENTAT_REQUEST_POOL_WIDTH="6")
unit <- list(id="sample",company="Sample",cycle=2026L,kind="employer",phase="P1_employer",variants="SAMPLE",query_field="contributor_employer",query_filters=list())
windows <- fec_api_date_windows(unit)
stopifnot(length(windows)==26L, is.null(windows[[1]]$query_filters$min_date),is.null(windows[[26]]$query_filters$max_date))
for(i in 1:25)stopifnot(as.Date(windows[[i]]$query_filters$max_date,"%m/%d/%Y")+1==as.Date(windows[[i+1]]$query_filters$min_date,"%m/%d/%Y"))
mode <- "complete"; widths <- integer(); checkpoints <- list()
transport <- function(specs,api_key,concurrency){
  widths <<- c(widths,length(specs))
  lapply(specs,function(spec){
    index <- if(grepl("::window::",spec$id,fixed=TRUE))as.integer(sub(".*::window::","",spec$id)) else 0L
    ids <- if(index)seq((index-1L)*100L+1L,index*100L) else 1:100
    if(mode=="overlap" && index==2L)ids<-1:100
    if(mode=="short" && index==26L)ids<-ids[-100]
    list(status=200L,body=list(results=lapply(ids,function(id)list(sub_id=as.character(id))),pagination=list(is_count_exact=TRUE,count=if(index)length(ids) else 2600L,last_indexes=if(index)list() else list(last_index="100",last_contribution_receipt_date="2026-12-31"))))
  })
}
result <- fec_api_collect_work_units(list(unit),api_key="fake",concurrency=6L,transport=transport,page_callback=function(state,page)checkpoints[[state$unit$id]] <<- state)
stopifnot(result$rows==2600L,max(widths)==6L,result$units$sample$complete,length(checkpoints)==27L)
for(bad in c("overlap","short")){
  mode<-bad
  error<-tryCatch({fec_api_collect_work_units(list(unit),api_key="fake",concurrency=6L,transport=transport);""},error=conditionMessage)
  stopifnot(grepl("coverage is partial or overlapping",error,fixed=TRUE))
}
mode<-"complete"
# A restart reuses complete child checkpoints, preserving parent publication gating.
restored<-checkpoints[startsWith(names(checkpoints),"sample::window::")]
widths<-integer()
again<-fec_api_collect_work_units(list(unit),api_key="fake",concurrency=6L,transport=transport,initial_states=restored)
stopifnot(again$rows==2600L,identical(widths,1L))
Sys.unsetenv("MENTAT_REQUEST_POOL_WIDTH")
cat("Shared request date windows, complete union, overlap/missing rejection, checkpoint resume: PASS\n")
