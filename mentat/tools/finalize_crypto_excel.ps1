param(
  [Parameter(Mandatory = $true)][string]$WorkbookPath,
  [Parameter(Mandatory = $true)][string]$JsonPath
)
$ErrorActionPreference = 'Stop'

function Release-ComObject($Object) {
  if ($null -ne $Object -and [Runtime.InteropServices.Marshal]::IsComObject($Object)) {
    [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($Object)
  }
}

function Set-TableColumnFormula($Table, [string]$ColumnName, [string]$Formula) {
  $column = $Table.ListColumns.Item($ColumnName)
  $range = $column.DataBodyRange
  try { $range.Formula = $Formula } finally { Release-ComObject $range; Release-ComObject $column }
}

function Cycle-Dispatch([scriptblock]$Builder) {
  $a = & $Builder 'Cycle_2021_2022'
  $b = & $Builder 'Cycle_2023_2024'
  $c = & $Builder 'Cycle_2025_2026'
  "IF([@Cycle]=`"2021-2022`",${a},IF([@Cycle]=`"2023-2024`",${b},${c}))"
}

function Scope-Expression([string]$TableName, [string]$Party = '') {
  $partyArgs = if ($Party) { ",${TableName}[Party],`"${Party}`"" } else { '' }
  $total = if ($Party) { "SUMIFS(${TableName}[Analysis Amount],${TableName}[Party],`"${Party}`")" } else { "SUM(${TableName}[Analysis Amount])" }
  $role = "SUMIFS(${TableName}[Analysis Amount],${TableName}[Employee Tier],[@Scope]${partyArgs})"
  $category = "SUMIFS(${TableName}[Analysis Amount],${TableName}[Recipient Category],[@Scope]${partyArgs})"
  "IF([@Scope]=`"Total Giving`",${total},IF(OR([@Scope]=`"Corporate`",[@Scope]=`"Chief`",[@Scope]=`"Middle Management`",[@Scope]=`"Employee`"),${role},${category}))"
}

function Company-Expression([string]$TableName, [string]$Party = '', [string]$Tier = '') {
  $extra = ''
  if ($Party) { $extra += ",${TableName}[Party],`"${Party}`"" }
  if ($Tier) { $extra += ",${TableName}[Employee Tier],`"${Tier}`"" }
  "SUMIFS(${TableName}[Analysis Amount],${TableName}[Company],[@Company]${extra})"
}

function Master-Expression([string]$TableName, [string]$Party = '', [string]$Category = '', [string]$Tier = '') {
  $extra = ''
  if ($Party) { $extra += ",${TableName}[Party],`"${Party}`"" }
  if ($Category) { $extra += ",${TableName}[Recipient Category],`"${Category}`"" }
  if ($Tier) { $extra += ",${TableName}[Employee Tier],`"${Tier}`"" }
  $industry = if ($extra) { "SUMIFS(${TableName}[Analysis Amount]${extra})" } else { "SUM(${TableName}[Analysis Amount])" }
  $company = "SUMIFS(${TableName}[Analysis Amount],${TableName}[Company],[@Company]${extra})"
  "IF([@Company]=`"Industry Total`",${industry},${company})"
}

function Master-Prior-Expression([string]$PriorCycle, [string]$Metric) {
  if (-not $PriorCycle) { return '0' }
  $industry = "SUMIFS(CompanyListTable[${Metric}],CompanyListTable[Cycle],`"${PriorCycle}`")"
  $company = "SUMIFS(CompanyListTable[${Metric}],CompanyListTable[Cycle],`"${PriorCycle}`",CompanyListTable[Company],[@Company])"
  "IF([@Company]=`"Industry Total`",${industry},${company})"
}

function Employee-Expression([string]$TableName, [string]$Party = '', [switch]$Count) {
  $partyArgs = if ($Party) { ",${TableName}[Party],`"${Party}`"" } else { '' }
  if ($Count) { return "COUNTIFS(${TableName}[Person Key],[@[Person Key]],${TableName}[Include in Analysis],`"Yes`")" }
  "SUMIFS(${TableName}[Analysis Amount],${TableName}[Person Key],[@[Person Key]]${partyArgs})"
}

function Recipient-Expression([string]$TableName, [string]$Party = '', [string]$Tier = '', [switch]$Count) {
  $extra = ''
  if ($Party) { $extra += ",${TableName}[Party],`"${Party}`"" }
  if ($Tier) { $extra += ",${TableName}[Employee Tier],`"${Tier}`"" }
  if ($Count) {
    $industry = "COUNTIFS(${TableName}[Recipient Key],[@[Recipient Key]],${TableName}[Include in Analysis],`"Yes`")"
    $company = "COUNTIFS(${TableName}[Recipient Key],[@[Recipient Key]],${TableName}[Company],[@Company],${TableName}[Include in Analysis],`"Yes`")"
  } else {
    $industry = "SUMIFS(${TableName}[Analysis Amount],${TableName}[Recipient Key],[@[Recipient Key]]${extra})"
    $company = "SUMIFS(${TableName}[Analysis Amount],${TableName}[Recipient Key],[@[Recipient Key]],${TableName}[Company],[@Company]${extra})"
  }
  "IF([@View]=`"Industry`",${industry},${company})"
}

function Bridge-Funding-Expression([string]$TableName) {
  $industry = "SUMIFS(${TableName}[Analysis Amount],${TableName}[Recipient Key],`"FEC:`"&[@[Source Committee ID]])"
  $company = "SUMIFS(${TableName}[Analysis Amount],${TableName}[Recipient Key],`"FEC:`"&[@[Source Committee ID]],${TableName}[Company],[@Company])"
  "IF([@View]=`"Industry`",${industry},${company})"
}

function Focused-Expression([string]$Metric) {
  $beneficiaryMetric = if ($Metric -eq 'Total Giving') { 'Downstream Activity' } elseif ($Metric -eq 'Other / Unclassified') { 'Other / Unclassified Activity' } else { "$Metric Activity" }
  $company = "SUMIFS(CompanyListTable[${Metric}],CompanyListTable[Cycle],[@Cycle],CompanyListTable[Company],[@[Reference Company]])"
  $employee = "SUMIFS(EmployeeListTable[${Metric}],EmployeeListTable[Cycle],[@Cycle],EmployeeListTable[Person Key],[@[Reference Key]])"
  $recipient = "SUMIFS(RecipientListTable[${Metric}],RecipientListTable[Cycle],[@Cycle],RecipientListTable[View],[@[Reference View]],RecipientListTable[Company],[@[Reference Company]],RecipientListTable[Recipient Key],[@[Reference Key]])"
  $beneficiary = "SUMIFS(BeneficiarySummaryTable[${beneficiaryMetric}],BeneficiarySummaryTable[Cycle],[@Cycle],BeneficiarySummaryTable[View],[@[Reference View]],BeneficiarySummaryTable[Company],[@[Reference Company]],BeneficiarySummaryTable[Candidate ID],[@[Reference Key]])"
  "IF([@Section]=`"Company Total`",${company},IF([@Section]=`"Top Contributor`",${employee},IF([@Section]=`"Top Direct Recipient`",${recipient},${beneficiary})))"
}

function Count-NonOk($Range) {
  $values = $Range.Value2; $bad = 0
  if ($values -is [Array]) {
    for ($row = $values.GetLowerBound(0); $row -le $values.GetUpperBound(0); $row++) {
      if ([string]$values.GetValue($row, 1) -ne 'OK') { $bad++ }
    }
  } elseif ([string]$values -ne 'OK') { $bad++ }
  $bad
}

$resolvedWorkbook = (Resolve-Path -LiteralPath $WorkbookPath).Path
$resolvedJson = (Resolve-Path -LiteralPath $JsonPath).Path
$payload = Get-Content -Raw -LiteralPath $resolvedJson | ConvertFrom-Json
$workingPath = Join-Path (Split-Path $resolvedWorkbook -Parent) 'Crypto Industry Spending Overview.excel-final.xlsx'
Copy-Item -LiteralPath $resolvedWorkbook -Destination $workingPath -Force
$excel = $null; $book = $null; $watch = [Diagnostics.Stopwatch]::StartNew()
try {
  $excel = New-Object -ComObject Excel.Application
  $excel.Visible = $false; $excel.DisplayAlerts = $false; $excel.EnableEvents = $false
  $book = $excel.Workbooks.Open($workingPath, 0, $false)
  $excel.Calculation = -4135

  foreach ($sheetName in @('2021-2022','2023-2024','2025-2026')) {
    $sheet = $book.Worksheets.Item($sheetName); $table = $sheet.ListObjects.Item(1)
    try {
      Set-TableColumnFormula $table 'Analysis Amount' '=IF([@[Include in Analysis]]="Yes",[@Amount],0)'
      Set-TableColumnFormula $table 'Logic Check' '=IF(AND([@[Analysis Amount]]=IF([@[Include in Analysis]]="Yes",[@Amount],0),OR([@[Cycle Alignment]]="OK",[@[Cycle Alignment]]="Reassigned by contribution date")),"OK","CHECK")'
    } finally { Release-ComObject $table; Release-ComObject $sheet }
  }
  $sheet = $book.Worksheets.Item('Cycle Exceptions'); $table = $sheet.ListObjects.Item(1)
  try {
    Set-TableColumnFormula $table 'Analysis Amount' '=IF([@[Include in Analysis]]="Yes",[@Amount],0)'
    Set-TableColumnFormula $table 'Logic Check' '=IF(AND([@[Include in Analysis]]="No",[@[Cycle Alignment]]="Outside requested cycles",[@[Analysis Amount]]=0),"OK","CHECK")'
  } finally { Release-ComObject $table; Release-ComObject $sheet }

  $sheet = $book.Worksheets.Item('Crypto Spending Overview'); $table = $sheet.ListObjects.Item(1)
  try {
    Set-TableColumnFormula $table 'Total Giving' ('=' + (Cycle-Dispatch { param($t) Scope-Expression $t }))
    Set-TableColumnFormula $table 'Democratic' ('=' + (Cycle-Dispatch { param($t) Scope-Expression $t 'D' }))
    Set-TableColumnFormula $table 'Republican' ('=' + (Cycle-Dispatch { param($t) Scope-Expression $t 'R' }))
    Set-TableColumnFormula $table 'Other / Unclassified' '=[@[Total Giving]]-[@Democratic]-[@Republican]'
    Set-TableColumnFormula $table 'Net Democratic %' '=IF([@Democratic]+[@Republican]=0,0,[@Democratic]/([@Democratic]+[@Republican]))'
    Set-TableColumnFormula $table 'Net Republican %' '=IF([@Democratic]+[@Republican]=0,0,[@Republican]/([@Democratic]+[@Republican]))'
    Set-TableColumnFormula $table 'Party Coverage' '=IF([@[Total Giving]]=0,0,([@Democratic]+[@Republican])/[@[Total Giving]])'
    Set-TableColumnFormula $table 'Integrity Check' '=IF(ABS([@[Total Giving]]-[@Democratic]-[@Republican]-[@[Other / Unclassified]])<0.01,"OK","CHECK")'
  } finally { Release-ComObject $table; Release-ComObject $sheet }

  $masterCategories = @('Super PAC','Carey','Company PAC','Leadership PAC','Trade Association','Candidate','Party Committee','JFC','Unclassified')
  $masterTiers = @('Corporate','Chief','Middle Management','Employee')
  $cycleEntries = @($payload.cycles | Sort-Object { [int]$_.cycle })
  $masterSpecs = @()
  for ($cycleIndex = 0; $cycleIndex -lt $cycleEntries.Count; $cycleIndex++) {
    $cycleEntry = $cycleEntries[$cycleIndex]
    $masterSpecs += [pscustomobject]@{
      Cycle = [string]$cycleEntry.label
      SourceTable = [string]$cycleEntry.table_name
      MasterTable = 'MasterOverview_' + [string]$cycleEntry.cycle
      PriorCycle = if ($cycleIndex -gt 0) { [string]$cycleEntries[$cycleIndex - 1].label } else { '' }
    }
  }
  $sheet = $book.Worksheets.Item('Master Overview')
  try {
    foreach ($spec in $masterSpecs) {
      $table = $sheet.ListObjects.Item([string]$spec.MasterTable)
      try {
        $masterTableName = [string]$spec.MasterTable
        $sourceTableName = [string]$spec.SourceTable
        $priorCycle = [string]$spec.PriorCycle
        $priorTotal = Master-Prior-Expression $priorCycle 'Total Giving'
        $priorDemocratic = Master-Prior-Expression $priorCycle 'Democratic'
        $priorRepublican = Master-Prior-Expression $priorCycle 'Republican'
        Set-TableColumnFormula $table 'Rank' ("=IF([@Company]=`"Industry Total`",0,1+COUNTIFS(${masterTableName}[Company],`"<>Industry Total`",${masterTableName}[Total Giving],`">`"&[@[Total Giving]]))")
        Set-TableColumnFormula $table 'Total Giving' ('=' + (Master-Expression $sourceTableName))
        Set-TableColumnFormula $table '% of Industry' ("=IFERROR([@[Total Giving]]/SUMIFS(${masterTableName}[Total Giving],${masterTableName}[Company],`"Industry Total`"),0)")
        Set-TableColumnFormula $table 'Democratic' ('=' + (Master-Expression $sourceTableName 'D'))
        Set-TableColumnFormula $table 'Republican' ('=' + (Master-Expression $sourceTableName 'R'))
        Set-TableColumnFormula $table 'Other / Unclassified' '=[@[Total Giving]]-[@Democratic]-[@Republican]'
        Set-TableColumnFormula $table 'Net Democratic %' '=IF([@Democratic]+[@Republican]=0,0,[@Democratic]/([@Democratic]+[@Republican]))'
        Set-TableColumnFormula $table 'Net Republican %' '=IF([@Democratic]+[@Republican]=0,0,[@Republican]/([@Democratic]+[@Republican]))'
        Set-TableColumnFormula $table 'Party Coverage' '=IF([@[Total Giving]]=0,0,([@Democratic]+[@Republican])/[@[Total Giving]])'
        Set-TableColumnFormula $table 'Prior Cycle' ('=' + $priorTotal)
        if ($priorCycle) {
          Set-TableColumnFormula $table '$ Change' '=[@[Total Giving]]-[@[Prior Cycle]]'
          Set-TableColumnFormula $table '% Change' '=IF([@[Prior Cycle]]=0,0,[@[$ Change]]/ABS([@[Prior Cycle]]))'
          Set-TableColumnFormula $table 'D $ Change' ("=[@Democratic]-(${priorDemocratic})")
          Set-TableColumnFormula $table 'R $ Change' ("=[@Republican]-(${priorRepublican})")
          Set-TableColumnFormula $table 'D Share Change' ("=[@[Net Democratic %]]-IF((${priorDemocratic})+(${priorRepublican})=0,0,(${priorDemocratic})/((${priorDemocratic})+(${priorRepublican})))")
          Set-TableColumnFormula $table 'R Share Change' ("=[@[Net Republican %]]-IF((${priorDemocratic})+(${priorRepublican})=0,0,(${priorRepublican})/((${priorDemocratic})+(${priorRepublican})))")
        } else {
          Set-TableColumnFormula $table '$ Change' '=0'
          Set-TableColumnFormula $table '% Change' '=0'
          Set-TableColumnFormula $table 'D $ Change' '=0'
          Set-TableColumnFormula $table 'R $ Change' '=0'
          Set-TableColumnFormula $table 'D Share Change' '=0'
          Set-TableColumnFormula $table 'R Share Change' '=0'
        }
        foreach ($category in $masterCategories) {
          Set-TableColumnFormula $table $category ('=' + (Master-Expression $sourceTableName '' $category))
          Set-TableColumnFormula $table "${category} %" ("=IF([@[Total Giving]]=0,0,[@[${category}]]/[@[Total Giving]])")
          Set-TableColumnFormula $table "${category} D" ('=' + (Master-Expression $sourceTableName 'D' $category))
          Set-TableColumnFormula $table "${category} R" ('=' + (Master-Expression $sourceTableName 'R' $category))
          Set-TableColumnFormula $table "${category} R %" ("=IF([@[${category} D]]+[@[${category} R]]=0,0,[@[${category} R]]/([@[${category} D]]+[@[${category} R]]))")
        }
        foreach ($tier in $masterTiers) {
          Set-TableColumnFormula $table $tier ('=' + (Master-Expression $sourceTableName '' '' $tier))
          Set-TableColumnFormula $table "${tier} %" ("=IF([@[Total Giving]]=0,0,[@[${tier}]]/[@[Total Giving]])")
          Set-TableColumnFormula $table "${tier} D" ('=' + (Master-Expression $sourceTableName 'D' '' $tier))
          Set-TableColumnFormula $table "${tier} R" ('=' + (Master-Expression $sourceTableName 'R' '' $tier))
          Set-TableColumnFormula $table "${tier} R %" ("=IF([@[${tier} D]]+[@[${tier} R]]=0,0,[@[${tier} R]]/([@[${tier} D]]+[@[${tier} R]]))")
        }
        $categorySum = ($masterCategories | ForEach-Object { "[@[${_}]]" }) -join '+'
        $tierSum = ($masterTiers | ForEach-Object { "[@[${_}]]" }) -join '+'
        Set-TableColumnFormula $table 'Integrity Check' ("=IF(AND(ABS([@[Total Giving]]-[@Democratic]-[@Republican]-[@[Other / Unclassified]])<0.01,ABS([@[Total Giving]]-(${categorySum}))<0.01,ABS([@[Total Giving]]-(${tierSum}))<0.01),`"OK`",`"CHECK`")")
      } finally { Release-ComObject $table }
    }
  } finally { Release-ComObject $sheet }

  $sheet = $book.Worksheets.Item('Company List'); $table = $sheet.ListObjects.Item(1)
  try {
    Set-TableColumnFormula $table 'Rank' '=1+COUNTIFS(CompanyListTable[Cycle],[@Cycle],CompanyListTable[Total Giving],">"&[@[Total Giving]])'
    Set-TableColumnFormula $table 'Total Giving' ('=' + (Cycle-Dispatch { param($t) Company-Expression $t }))
    Set-TableColumnFormula $table 'Democratic' ('=' + (Cycle-Dispatch { param($t) Company-Expression $t 'D' }))
    Set-TableColumnFormula $table 'Republican' ('=' + (Cycle-Dispatch { param($t) Company-Expression $t 'R' }))
    Set-TableColumnFormula $table 'Other / Unclassified' '=[@[Total Giving]]-[@Democratic]-[@Republican]'
    Set-TableColumnFormula $table 'Net Democratic %' '=IF([@Democratic]+[@Republican]=0,0,[@Democratic]/([@Democratic]+[@Republican]))'
    Set-TableColumnFormula $table 'Net Republican %' '=IF([@Democratic]+[@Republican]=0,0,[@Republican]/([@Democratic]+[@Republican]))'
    Set-TableColumnFormula $table 'Party Coverage' '=IF([@[Total Giving]]=0,0,([@Democratic]+[@Republican])/[@[Total Giving]])'
    foreach ($tier in @('Corporate','Chief','Middle Management','Employee')) {
      Set-TableColumnFormula $table $tier ('=' + (Cycle-Dispatch { param($t) Company-Expression $t '' $tier }))
    }
    Set-TableColumnFormula $table 'Integrity Check' '=IF(AND(ABS([@[Total Giving]]-[@Democratic]-[@Republican]-[@[Other / Unclassified]])<0.01,ABS([@[Total Giving]]-[@Corporate]-[@Chief]-[@[Middle Management]]-[@Employee])<0.01),"OK","CHECK")'
  } finally { Release-ComObject $table; Release-ComObject $sheet }

  $sheet = $book.Worksheets.Item('Employee List'); $table = $sheet.ListObjects.Item(1)
  try {
    Set-TableColumnFormula $table 'Industry Rank' '=1+COUNTIFS(EmployeeListTable[Cycle],[@Cycle],EmployeeListTable[Total Giving],">"&[@[Total Giving]])'
    Set-TableColumnFormula $table 'Company Rank' '=1+COUNTIFS(EmployeeListTable[Cycle],[@Cycle],EmployeeListTable[Company],[@Company],EmployeeListTable[Total Giving],">"&[@[Total Giving]])'
    Set-TableColumnFormula $table 'Total Giving' ('=' + (Cycle-Dispatch { param($t) Employee-Expression $t }))
    Set-TableColumnFormula $table 'Democratic' ('=' + (Cycle-Dispatch { param($t) Employee-Expression $t 'D' }))
    Set-TableColumnFormula $table 'Republican' ('=' + (Cycle-Dispatch { param($t) Employee-Expression $t 'R' }))
    Set-TableColumnFormula $table 'Other / Unclassified' '=[@[Total Giving]]-[@Democratic]-[@Republican]'
    Set-TableColumnFormula $table 'Net Democratic %' '=IF([@Democratic]+[@Republican]=0,0,[@Democratic]/([@Democratic]+[@Republican]))'
    Set-TableColumnFormula $table 'Net Republican %' '=IF([@Democratic]+[@Republican]=0,0,[@Republican]/([@Democratic]+[@Republican]))'
    Set-TableColumnFormula $table 'Party Coverage' '=IF([@[Total Giving]]=0,0,([@Democratic]+[@Republican])/[@[Total Giving]])'
    Set-TableColumnFormula $table 'Contribution Count' ('=' + (Cycle-Dispatch { param($t) Employee-Expression $t '' -Count }))
    Set-TableColumnFormula $table 'Integrity Check' '=IF(ABS([@[Total Giving]]-[@Democratic]-[@Republican]-[@[Other / Unclassified]])<0.01,"OK","CHECK")'
  } finally { Release-ComObject $table; Release-ComObject $sheet }

  $sheet = $book.Worksheets.Item('Recipient List'); $table = $sheet.ListObjects.Item(1)
  try {
    Set-TableColumnFormula $table 'Rank' '=1+COUNTIFS(RecipientListTable[Cycle],[@Cycle],RecipientListTable[View],[@View],RecipientListTable[Company],[@Company],RecipientListTable[Total Giving],">"&[@[Total Giving]])'
    Set-TableColumnFormula $table 'Direct Candidate / Sponsor' '=XLOOKUP([@Cycle]&"|"&[@[Committee ID]],PACMapTable[Lookup Key],PACMapTable[Direct Candidate / Sponsor],"")'
    Set-TableColumnFormula $table 'Committee Relationship' '=XLOOKUP([@Cycle]&"|"&[@[Committee ID]],PACMapTable[Lookup Key],PACMapTable[Relationship],"")'
    Set-TableColumnFormula $table 'Ownership Status' '=XLOOKUP([@Cycle]&"|"&[@[Committee ID]],PACMapTable[Lookup Key],PACMapTable[Ownership Status],"")'
    Set-TableColumnFormula $table 'Top Downstream Congressional Beneficiary' '=XLOOKUP([@Cycle]&"|"&[@[Committee ID]],PACMapTable[Lookup Key],PACMapTable[Top Downstream Congressional Beneficiary],"")'
    Set-TableColumnFormula $table 'Top Downstream Candidate ID' '=XLOOKUP([@Cycle]&"|"&[@[Committee ID]],PACMapTable[Lookup Key],PACMapTable[Top Downstream Candidate ID],"")'
    Set-TableColumnFormula $table 'Top Downstream Activity' '=IF([@[Top Downstream Candidate ID]]="",0,SUMIFS(DownstreamActivityTable[Net Included Amount],DownstreamActivityTable[Cycle],[@Cycle],DownstreamActivityTable[Source Committee ID],[@[Committee ID]],DownstreamActivityTable[Candidate ID],[@[Top Downstream Candidate ID]]))'
    Set-TableColumnFormula $table 'Total Giving' ('=' + (Cycle-Dispatch { param($t) Recipient-Expression $t }))
    Set-TableColumnFormula $table 'Democratic' ('=' + (Cycle-Dispatch { param($t) Recipient-Expression $t 'D' }))
    Set-TableColumnFormula $table 'Republican' ('=' + (Cycle-Dispatch { param($t) Recipient-Expression $t 'R' }))
    Set-TableColumnFormula $table 'Other / Unclassified' '=[@[Total Giving]]-[@Democratic]-[@Republican]'
    Set-TableColumnFormula $table 'Net Democratic %' '=IF([@Democratic]+[@Republican]=0,0,[@Democratic]/([@Democratic]+[@Republican]))'
    Set-TableColumnFormula $table 'Net Republican %' '=IF([@Democratic]+[@Republican]=0,0,[@Republican]/([@Democratic]+[@Republican]))'
    Set-TableColumnFormula $table 'Party Coverage' '=IF([@[Total Giving]]=0,0,([@Democratic]+[@Republican])/[@[Total Giving]])'
    foreach ($tier in @('Corporate','Chief','Middle Management','Employee')) {
      Set-TableColumnFormula $table $tier ('=' + (Cycle-Dispatch { param($t) Recipient-Expression $t '' $tier }))
    }
    Set-TableColumnFormula $table 'Contribution Count' ('=' + (Cycle-Dispatch { param($t) Recipient-Expression $t '' '' -Count }))
    Set-TableColumnFormula $table 'FEC Committee URL' '=IF([@[Committee ID]]="","","https://www.fec.gov/data/committee/"&[@[Committee ID]]&"/")'
    Set-TableColumnFormula $table 'Integrity Check' '=IF(AND(ABS([@[Total Giving]]-[@Democratic]-[@Republican]-[@[Other / Unclassified]])<0.01,ABS([@[Total Giving]]-[@Corporate]-[@Chief]-[@[Middle Management]]-[@Employee])<0.01),"OK","CHECK")'
  } finally { Release-ComObject $table; Release-ComObject $sheet }

  $sheet = $book.Worksheets.Item('PAC & Candidate Map'); $table = $sheet.ListObjects.Item(1)
  try {
    Set-TableColumnFormula $table 'Top Downstream Activity' '=IF([@[Top Downstream Candidate ID]]="",0,SUMIFS(DownstreamActivityTable[Net Included Amount],DownstreamActivityTable[Cycle],[@Cycle],DownstreamActivityTable[Source Committee ID],[@[Committee ID]],DownstreamActivityTable[Candidate ID],[@[Top Downstream Candidate ID]]))'
    Set-TableColumnFormula $table 'FEC Committee URL' '=IF([@[Committee ID]]="","","https://www.fec.gov/data/committee/"&[@[Committee ID]]&"/")'
    Set-TableColumnFormula $table 'FEC Candidate URL' '=IF(OR([@[Candidate ID(s)]]="",ISNUMBER(SEARCH(";",[@[Candidate ID(s)]]))),"","https://www.fec.gov/data/candidate/"&[@[Candidate ID(s)]]&"/")'
    Set-TableColumnFormula $table 'Integrity Check' '=IF(AND([@[Committee ID]]<>"",OR([@[Ownership Status]]="Organization/committee; no individual ownership link in FEC files",[@[Direct Candidate / Sponsor]]<>"")),"OK","CHECK")'
  } finally { Release-ComObject $table; Release-ComObject $sheet }

  $sheet = $book.Worksheets.Item('Downstream Activity'); $table = $sheet.ListObjects.Item(1)
  try {
    Set-TableColumnFormula $table 'Net Included Amount' '=[@[Reported Amount]]-[@[Excluded Amount]]'
    Set-TableColumnFormula $table 'FEC Committee URL' '=IF([@[Source Committee ID]]="","","https://www.fec.gov/data/committee/"&[@[Source Committee ID]]&"/")'
    Set-TableColumnFormula $table 'FEC Candidate URL' '=IF([@[Candidate ID]]="","","https://www.fec.gov/data/candidate/"&[@[Candidate ID]]&"/")'
    Set-TableColumnFormula $table 'Logic Check' '=IF(AND([@[Source Rows]]=[@[Included Rows]]+[@[Excluded Rows]],ABS([@[Net Included Amount]]-([@[Reported Amount]]-[@[Excluded Amount]]))<0.01),"OK","CHECK")'
  } finally { Release-ComObject $table; Release-ComObject $sheet }

  $sheet = $book.Worksheets.Item('Beneficiary Bridge'); $table = $sheet.ListObjects.Item(1)
  try {
    Set-TableColumnFormula $table 'Downstream Activity' '=SUMIFS(DownstreamActivityTable[Net Included Amount],DownstreamActivityTable[Cycle],[@Cycle],DownstreamActivityTable[Source Committee ID],[@[Source Committee ID]],DownstreamActivityTable[Candidate ID],[@[Candidate ID]])'
    Set-TableColumnFormula $table 'Associated Crypto Funding' ('=' + (Cycle-Dispatch { param($t) Bridge-Funding-Expression $t }))
    Set-TableColumnFormula $table 'FEC Committee URL' '=IF([@[Source Committee ID]]="","","https://www.fec.gov/data/committee/"&[@[Source Committee ID]]&"/")'
    Set-TableColumnFormula $table 'FEC Candidate URL' '=IF([@[Candidate ID]]="","","https://www.fec.gov/data/candidate/"&[@[Candidate ID]]&"/")'
    Set-TableColumnFormula $table 'Integrity Check' '=IF(AND([@[Source Committee ID]]<>"",[@[Candidate ID]]<>"",ISNUMBER([@[Downstream Activity]]),ISNUMBER([@[Associated Crypto Funding]])),"OK","CHECK")'
  } finally { Release-ComObject $table; Release-ComObject $sheet }

  $sheet = $book.Worksheets.Item('Beneficiary Summary'); $table = $sheet.ListObjects.Item(1)
  try {
    Set-TableColumnFormula $table 'Rank' '=1+COUNTIFS(BeneficiarySummaryTable[Cycle],[@Cycle],BeneficiarySummaryTable[View],[@View],BeneficiarySummaryTable[Company],[@Company],BeneficiarySummaryTable[Downstream Activity],">"&[@[Downstream Activity]])'
    Set-TableColumnFormula $table 'Downstream Activity' '=SUMIFS(BeneficiaryBridgeTable[Downstream Activity],BeneficiaryBridgeTable[Cycle],[@Cycle],BeneficiaryBridgeTable[View],[@View],BeneficiaryBridgeTable[Company],[@Company],BeneficiaryBridgeTable[Candidate ID],[@[Candidate ID]])'
    Set-TableColumnFormula $table 'Associated Crypto Funding' '=SUMIFS(BeneficiaryBridgeTable[Associated Crypto Funding],BeneficiaryBridgeTable[Cycle],[@Cycle],BeneficiaryBridgeTable[View],[@View],BeneficiaryBridgeTable[Company],[@Company],BeneficiaryBridgeTable[Candidate ID],[@[Candidate ID]])'
    Set-TableColumnFormula $table 'Democratic Activity' '=IF([@Party]="D",[@[Downstream Activity]],0)'
    Set-TableColumnFormula $table 'Republican Activity' '=IF([@Party]="R",[@[Downstream Activity]],0)'
    Set-TableColumnFormula $table 'Other / Unclassified Activity' '=[@[Downstream Activity]]-[@[Democratic Activity]]-[@[Republican Activity]]'
    Set-TableColumnFormula $table 'Party Coverage' '=IF([@[Downstream Activity]]=0,0,([@[Democratic Activity]]+[@[Republican Activity]])/[@[Downstream Activity]])'
    Set-TableColumnFormula $table 'FEC Candidate URL' '=IF([@[Candidate ID]]="","","https://www.fec.gov/data/candidate/"&[@[Candidate ID]]&"/")'
    Set-TableColumnFormula $table 'Integrity Check' '=IF(ABS([@[Downstream Activity]]-[@[Democratic Activity]]-[@[Republican Activity]]-[@[Other / Unclassified Activity]])<0.01,"OK","CHECK")'
  } finally { Release-ComObject $table; Release-ComObject $sheet }

  $focusedSheets = @()
  foreach ($cycle in $payload.cycles) { $focusedSheets += ([string]$cycle.label + ' Summary') }
  foreach ($company in $payload.companies) { $focusedSheets += (([string]$company + ' View').Substring(0,[math]::Min(31,([string]$company + ' View').Length))) }
  foreach ($sheetName in $focusedSheets) {
    $sheet = $book.Worksheets.Item($sheetName); $table = $sheet.ListObjects.Item(1)
    try {
      $tableName = [string]$table.Name
      Set-TableColumnFormula $table 'Rank' ("=1+COUNTIFS(${tableName}[Cycle],[@Cycle],${tableName}[Section],[@Section],${tableName}[Total / Activity],`">`"&[@[Total / Activity]])")
      Set-TableColumnFormula $table 'Total / Activity' ('=' + (Focused-Expression 'Total Giving'))
      Set-TableColumnFormula $table 'Democratic' ('=' + (Focused-Expression 'Democratic'))
      Set-TableColumnFormula $table 'Republican' ('=' + (Focused-Expression 'Republican'))
      Set-TableColumnFormula $table 'Other / Unclassified' ('=' + (Focused-Expression 'Other / Unclassified'))
      Set-TableColumnFormula $table 'Party Coverage' '=IF([@[Total / Activity]]=0,0,([@Democratic]+[@Republican])/[@[Total / Activity]])'
      Set-TableColumnFormula $table 'Integrity Check' '=IF(ABS([@[Total / Activity]]-[@Democratic]-[@Republican]-[@[Other / Unclassified]])<0.01,"OK","CHECK")'
    } finally { Release-ComObject $table; Release-ComObject $sheet }
  }

  $headerRows = @{
    'Master Overview'=6;'Crypto Spending Overview'=5;'Company List'=5;'Employee List'=5;'Recipient List'=5
    'Beneficiary Summary'=5;'PAC & Candidate Map'=5;'Downstream Activity'=5;'Beneficiary Bridge'=5
    '2021-2022'=4;'2023-2024'=4;'2025-2026'=4;'Cycle Exceptions'=4
  }
  foreach ($sheetName in $focusedSheets) { $headerRows[$sheetName] = 5 }
  foreach ($sheetName in $headerRows.Keys) {
    $sheet = $book.Worksheets.Item($sheetName); $sheet.Activate(); $excel.ActiveWindow.FreezePanes = $false
    $excel.ActiveWindow.SplitColumn = 0; $excel.ActiveWindow.SplitRow = $headerRows[$sheetName]; $excel.ActiveWindow.FreezePanes = $true
    Release-ComObject $sheet
  }
  $excel.Calculation = -4105; $excel.CalculateFullRebuild()
  while ($excel.CalculationState -ne 0) { Start-Sleep -Milliseconds 100 }

  $formulaColumnsBySheet = @{
    'Crypto Spending Overview'=@('Total Giving','Democratic','Republican','Other / Unclassified','Net Democratic %','Net Republican %','Party Coverage','Integrity Check')
    'Company List'=@('Rank','Total Giving','Democratic','Republican','Other / Unclassified','Net Democratic %','Net Republican %','Party Coverage','Corporate','Chief','Middle Management','Employee','Integrity Check')
    'Employee List'=@('Industry Rank','Company Rank','Total Giving','Democratic','Republican','Other / Unclassified','Net Democratic %','Net Republican %','Party Coverage','Contribution Count','Integrity Check')
    'Recipient List'=@('Rank','Direct Candidate / Sponsor','Committee Relationship','Ownership Status','Top Downstream Congressional Beneficiary','Top Downstream Candidate ID','Top Downstream Activity','Total Giving','Democratic','Republican','Other / Unclassified','Net Democratic %','Net Republican %','Party Coverage','Corporate','Chief','Middle Management','Employee','Contribution Count','FEC Committee URL','Integrity Check')
    'PAC & Candidate Map'=@('Top Downstream Activity','FEC Committee URL','FEC Candidate URL','Integrity Check')
    'Downstream Activity'=@('Net Included Amount','FEC Committee URL','FEC Candidate URL','Logic Check')
    'Beneficiary Bridge'=@('Downstream Activity','Associated Crypto Funding','FEC Committee URL','FEC Candidate URL','Integrity Check')
    'Beneficiary Summary'=@('Rank','Downstream Activity','Associated Crypto Funding','Democratic Activity','Republican Activity','Other / Unclassified Activity','Party Coverage','FEC Candidate URL','Integrity Check')
    '2021-2022'=@('Analysis Amount','Logic Check');'2023-2024'=@('Analysis Amount','Logic Check');'2025-2026'=@('Analysis Amount','Logic Check');'Cycle Exceptions'=@('Analysis Amount','Logic Check')
  }
  foreach ($sheetName in $focusedSheets) {
    $formulaColumnsBySheet[$sheetName] = @('Rank','Total / Activity','Democratic','Republican','Other / Unclassified','Party Coverage','Integrity Check')
  }
  $formulaCount = 0L; $formulaColumnFailures = 0L; $integrityFailures = 0L
  foreach ($sheetName in $formulaColumnsBySheet.Keys) {
    $sheet = $book.Worksheets.Item($sheetName); $table = $sheet.ListObjects.Item(1)
    try {
      foreach ($columnName in $formulaColumnsBySheet[$sheetName]) {
        $column = $table.ListColumns.Item($columnName); $range = $column.DataBodyRange
        try { $formulaCount += [long]$range.Rows.Count; if ($range.HasFormula -ne $true) { $formulaColumnFailures++ } }
        finally { Release-ComObject $range; Release-ComObject $column }
      }
      $checkName = if ($sheetName -in @('2021-2022','2023-2024','2025-2026','Cycle Exceptions','Downstream Activity')) {'Logic Check'} else {'Integrity Check'}
      $column = $table.ListColumns.Item($checkName); $range = $column.DataBodyRange
      try { $integrityFailures += Count-NonOk $range } finally { Release-ComObject $range; Release-ComObject $column }
    } finally { Release-ComObject $table; Release-ComObject $sheet }
  }

  $masterFormulaColumns = @(
    'Rank','Total Giving','% of Industry','Democratic','Republican','Other / Unclassified',
    'Net Democratic %','Net Republican %','Party Coverage','Prior Cycle',
    '$ Change','% Change','D $ Change','R $ Change','D Share Change','R Share Change'
  )
  foreach ($category in $masterCategories) {
    $masterFormulaColumns += @($category,"${category} %","${category} D","${category} R","${category} R %")
  }
  foreach ($tier in $masterTiers) {
    $masterFormulaColumns += @($tier,"${tier} %","${tier} D","${tier} R","${tier} R %")
  }
  $masterFormulaColumns += 'Integrity Check'
  $sheet = $book.Worksheets.Item('Master Overview')
  try {
    foreach ($spec in $masterSpecs) {
      $table = $sheet.ListObjects.Item([string]$spec.MasterTable)
      try {
        foreach ($columnName in $masterFormulaColumns) {
          $column = $table.ListColumns.Item($columnName); $range = $column.DataBodyRange
          try { $formulaCount += [long]$range.Rows.Count; if ($range.HasFormula -ne $true) { $formulaColumnFailures++ } }
          finally { Release-ComObject $range; Release-ComObject $column }
        }
        $column = $table.ListColumns.Item('Integrity Check'); $range = $column.DataBodyRange
        try { $integrityFailures += Count-NonOk $range } finally { Release-ComObject $range; Release-ComObject $column }
      } finally { Release-ComObject $table }
    }
  } finally { Release-ComObject $sheet }

  $expectedTotals = @{}
  foreach ($cycle in @('2021-2022','2023-2024','2025-2026')) { $expectedTotals[$cycle] = 0.0 }
  foreach ($row in $payload.raw_rows) { if ($row.include_in_analysis -eq 'Yes') { $expectedTotals[[string]$row.cycle_label] += [double]$row.amount } }
  $sheet = $book.Worksheets.Item('Crypto Spending Overview'); $table = $sheet.ListObjects.Item(1); $rows = $table.DataBodyRange
  try {
    for ($index=1; $index -le $rows.Rows.Count; $index++) {
      if ([string]$rows.Cells.Item($index,2).Value2 -eq 'Total Giving') {
        $cycle=[string]$rows.Cells.Item($index,1).Value2; $actual=[double]$rows.Cells.Item($index,3).Value2
        if ([math]::Abs($actual-$expectedTotals[$cycle]) -ge 0.01) { throw "Cycle total mismatch for ${cycle}: actual=$actual expected=$($expectedTotals[$cycle])" }
      }
    }
  } finally { Release-ComObject $rows; Release-ComObject $table; Release-ComObject $sheet }
  $sheet = $book.Worksheets.Item('Master Overview')
  try {
    foreach ($spec in $masterSpecs) {
      $table = $sheet.ListObjects.Item([string]$spec.MasterTable); $rows = $table.DataBodyRange
      try {
        $industryTotal = $null; $companyTotal = 0.0
        for ($index=1; $index -le $rows.Rows.Count; $index++) {
          $company = [string]$rows.Cells.Item($index,1).Value2
          $total = [double]$rows.Cells.Item($index,3).Value2
          $prior = [double]$rows.Cells.Item($index,11).Value2
          $change = [double]$rows.Cells.Item($index,12).Value2
          if ([string]$spec.PriorCycle) {
            if ([math]::Abs(($total-$prior)-$change) -ge 0.01) {
              throw "Master Overview prior-cycle change mismatch for $($spec.Cycle) / ${company}"
            }
          } else {
            foreach ($columnIndex in 12..17) {
              if ([math]::Abs([double]$rows.Cells.Item($index,$columnIndex).Value2) -ge 0.000001) {
                throw "Master Overview oldest-cycle change should be blank/zero for $($spec.Cycle) / ${company}"
              }
            }
          }
          if ($company -eq 'Industry Total') { $industryTotal = $total } else { $companyTotal += $total }
        }
        $cycle = [string]$spec.Cycle
        if ($null -eq $industryTotal -or [math]::Abs($industryTotal-$expectedTotals[$cycle]) -ge 0.01) {
          throw "Master Overview industry total mismatch for ${cycle}: actual=$industryTotal expected=$($expectedTotals[$cycle])"
        }
        if ([math]::Abs($companyTotal-$industryTotal) -ge 0.01) {
          throw "Master Overview company sum mismatch for ${cycle}: companies=$companyTotal industry=$industryTotal"
        }
      } finally { Release-ComObject $rows; Release-ComObject $table }
    }
  } finally { Release-ComObject $sheet }
  if ($formulaColumnFailures -ne 0 -or $integrityFailures -ne 0 -or $formulaCount -lt 50000) {
    throw "Verification failed: formulas=$formulaCount formula_column_failures=$formulaColumnFailures integrity_failures=$integrityFailures"
  }
  if (([math]::Round($expectedTotals['2021-2022'],2) -eq [math]::Round($expectedTotals['2023-2024'],2)) -or ([math]::Round($expectedTotals['2023-2024'],2) -eq [math]::Round($expectedTotals['2025-2026'],2))) { throw 'Cycle totals unexpectedly identical' }

  $book.Save(); $book.Close($false); Release-ComObject $book; $book = $null
  $excel.Quit(); Release-ComObject $excel; $excel = $null
  Copy-Item -LiteralPath $workingPath -Destination $resolvedWorkbook -Force
  $watch.Stop()
  [pscustomobject]@{workbook=$resolvedWorkbook;bytes=(Get-Item -LiteralPath $resolvedWorkbook).Length;formulas=$formulaCount;formula_column_failures=$formulaColumnFailures;integrity_failures=$integrityFailures;cycle_totals=$expectedTotals;seconds=[math]::Round($watch.Elapsed.TotalSeconds,3)} | ConvertTo-Json -Depth 3
} finally {
  if ($null -ne $book) { try {$book.Close($false)} catch {}; Release-ComObject $book }
  if ($null -ne $excel) { try {$excel.Quit()} catch {}; Release-ComObject $excel }
}
