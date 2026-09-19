script <- sub('^--file=', '', grep('^--file=', commandArgs(FALSE), value=TRUE)[[1L]])
project <- normalizePath(file.path(dirname(script), '..'), winslash='/', mustWork=TRUE)
for (name in c('paths', 'ingest', 'collect', 'fec_beneficiary', 'fec_transfer_graph'))
  source(file.path(project, 'R', paste0(name, '.R')))
data.table::setDTthreads(2L)

check_transfer_evidence <- function() {
  directory <- tempfile('mentat-transfer-evidence-')
  dir.create(file.path(directory, 'pas224'), recursive=TRUE)
  on.exit(unlink(directory, recursive=TRUE))
  path <- file.path(directory, 'pas224', 'itpas2.txt')
  row <- function(date='12312023', file='1', sub='1', kind='24K', amendment='N') {
    fields <- rep('', 22L)
    fields[c(1,2,3,6,14,15,16,17,18,19,22)] <-
      c('C00000001', amendment, 'Q1', kind, date, '100', 'C00000002', 'H00000001', 'T1', file, sub)
    paste(fields, collapse='|')
  }
  aggregate <- function(index) {
    index[, `:=`(candidate_name='Candidate', candidate_party='Other', office='H',
      office_label='House', office_state='CA', district='1', candidate_source_url='fixture')]
    fec_aggregate_downstream_activity(index, data.table::data.table(cycle=2024L,
      committee_id='C00000001', committee_name='PAC', recipient_category='PAC'))
  }
  writeLines(row(), path)
  indexed <- fec_build_pas2_index(directory, 2024L)
  retained <- aggregate(indexed)
  evidence <- jsonlite::fromJSON(retained$transfer_records[[1L]])
  stopifnot(nrow(evidence)==1L, evidence$transaction_id=='T1', evidence$file_num==1,
    evidence$destination=='C00000002', evidence$cents==10000,
    retained$preliminary_included_amount==100)
  writeLines(c(row(), row(date='01012024',file='2',sub='2',amendment='A')), path)
  redated <- aggregate(fec_build_pas2_index(directory, 2024L))
  stopifnot(redated$unresolved_version_rows==2L, redated$preliminary_included_amount==0,
    redated$transfer_records=='[]')
  writeLines(c(row(), row(file='2',sub='2',kind='24Z',amendment='A')), path)
  reclassified <- fec_build_pas2_index(directory, 2024L)
  stopifnot(nrow(reclassified)==2L, all(reclassified$include_in_total=='No'))

  dir.create(file.path(directory, 'oth24'))
  info <- file.path(directory, 'oth24', 'transfer-info.json')
  jsonlite::write_json(list(version=2), info, auto_unbox=TRUE)
  roots <- data.table::data.table(cycle=2024L,committee_id='C00000001',preliminary_crypto_funding=100)
  links <- data.table::data.table(cycle=2024L,committee_id='C00000002',designation='P')
  stale <- fec_transfer_context(directory, roots, links, 2024L)
  stopifnot(stale$coverage[[1L]]$status=='stale_transfer_index', nrow(stale$edges)==0L)
  edges <- file.path(dirname(info), 'transfer-edges.csv')
  data.table::fwrite(data.table::data.table(cycle=2024L,source='C00000001',destination='C00000002',
    amount=100,records='[]'),edges)
  jsonlite::write_json(list(version=3,edges_sha256=digest::digest(file=edges,algo='sha256'),
    unresolved_sources=list('C00000001'),unresolved_all_sources=FALSE,counts=list(unresolved_rows=2)),
    info,auto_unbox=TRUE)
  current <- fec_transfer_context(directory,roots,links,2024L)
  encoded <- jsonlite::toJSON(current$coverage,auto_unbox=TRUE)
  stopifnot(grepl('"unresolved_sources":\\["C00000001"\\]',encoded))
  args <- commandArgs(TRUE)
  if (length(args)) jsonlite::write_json(list(downstream_activity=retained),args[[1L]],
    dataframe='rows',auto_unbox=TRUE,digits=NA)
}
check_transfer_evidence()
cat('Transfer evidence: retained identities, amendment review, cache version and coverage serialization PASS\n')
