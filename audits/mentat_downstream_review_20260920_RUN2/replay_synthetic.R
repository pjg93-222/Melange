script <- sub('^--file=', '', grep('^--file=',commandArgs(FALSE),value=TRUE)[[1]])
audit <- normalizePath(dirname(script),winslash='/')
project <- normalizePath(file.path(audit,'../../mentat'),winslash='/')
for (name in c('paths','ingest','collect','fec_beneficiary')) source(file.path(project,'R',paste0(name,'.R')))
data.table::setDTthreads(2L)
before <- new.env(parent=globalenv())
sys.source(file.path(audit,'before/mentat/R/fec_beneficiary.R'),envir=before)
root <- tempfile('downstream-ledger-');dir.create(file.path(root,'pas224'),recursive=TRUE)
fields <- rep('',22);fields[c(1,2,3,6,14,15,18,19,22)] <- c('ROOT','N','Q1','24E','01022024','123.45','T1','1','1')
writeLines(paste(fields,collapse='|'),file.path(root,'pas224/itpas2.txt'))
old <- before$fec_build_pas2_index(root,2024L);new <- fec_build_pas2_index(root,2024L)
entry <- function(name,a,b) list(case=name,before=a,after=b,delta=b-a,basis='Synthetic regression fixture, identical inputs')
ledger <- list(entry('Blank candidate ID retained as unknown',
  sum(old[include_in_total=='Yes',transaction_amount]),sum(new[include_in_total=='Yes',transaction_amount])))
funding <- data.table::data.table(cycle=2024L,company=c('A','B'),committee_id='ROOT',amount=100,
  recipient='Root',include_in_analysis='Yes')
activity <- data.table::data.table(cycle=2024L,committee_id='SPENDER',candidate_id=sprintf('H%08d',1:105),
  candidate_name=paste('Candidate',1:105),candidate_party='R',office='H',office_label='House',
  office_state='KY',district='06',transaction_amount=1:105,activity_type='Independent expenditure',
  support_oppose='Support',transaction_date='2024-01-02',include_in_total='Yes')
edges <- data.table::data.table(cycle=2024L,source='ROOT',destination='SPENDER',amount=50)
old <- before$fec_build_beneficiary_tables(funding,activity,edges)
new <- fec_build_beneficiary_tables(funding,activity,edges)
ledger[[2]] <- entry('Full unique Data activity beyond Overview top 100',
  sum(old$bridge[view=='Industry',preliminary_downstream_amount]),
  sum(new$bridge_all[view=='Industry',preliminary_downstream_amount]))
funding[company=='B',amount:=-200]
old <- before$fec_build_beneficiary_tables(funding,activity,edges)
new <- fec_build_beneficiary_tables(funding,activity,edges)
ledger[[3]] <- entry('Industry reach survives offsetting company refunds (pre-cutoff)',
  sum(old$measurement_ledger[view=='Industry',after_amount]),
  sum(new$measurement_ledger[view=='Industry',after_amount]))
jsonlite::write_json(ledger,file.path(audit,'synthetic_dollar_ledger.json'),pretty=TRUE,auto_unbox=TRUE,digits=NA)
unlink(root,recursive=TRUE)
cat('Preserved baseline/current synthetic dollar ledger complete\n')
