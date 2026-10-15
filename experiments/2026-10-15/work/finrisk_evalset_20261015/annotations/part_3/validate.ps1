$sourcePath = 'outputs\FinRisk_可用测试集_v1_20261015\annotation_inputs\part_3.jsonl'
$decisionPath = 'work\finrisk_evalset_20261015\annotations\part_3\decisions.jsonl'
$sourceRows = @(Get-Content -LiteralPath $sourcePath -Encoding UTF8 | ForEach-Object { $_ | ConvertFrom-Json })
$decisionRows = @(Get-Content -LiteralPath $decisionPath -Encoding UTF8 | ForEach-Object { $_ | ConvertFrom-Json })
$byId = @{}
foreach ($row in $sourceRows) { $byId[$row.file_id] = $row }
$errors = [System.Collections.Generic.List[string]]::new()
$counts = @(0,0,0,0)
$seen = @{}
$evidenceCount = 0
if ($sourceRows.Count -ne 33 -or $decisionRows.Count -ne 33) { $errors.Add('row count is not 33') }
foreach ($row in $decisionRows) {
  if ($seen.ContainsKey($row.file_id)) { $errors.Add(('duplicate: ' + $row.file_id)) }
  $seen[$row.file_id] = $true
  if (-not $byId.ContainsKey($row.file_id)) { $errors.Add(('unknown: ' + $row.file_id)); continue }
  if ($row.grades.Count -ne 20) { $errors.Add(('grades length: ' + $row.file_id)) }
  if ($row.all20_queries_reviewed -ne $true -or $row.human_approved -ne $false -or $row.origin -ne 'model_source_review' -or $row.reviewer_id -ne 'p3') { $errors.Add(('metadata: ' + $row.file_id)) }
  if ([string]::IsNullOrWhiteSpace($row.document_mechanism_summary)) { $errors.Add(('empty summary: ' + $row.file_id)) }
  for ($index = 0; $index -lt $row.grades.Count; $index++) {
    $grade = $row.grades[$index]
    $query = 'KBT{0:D3}' -f ($index + 1)
    if (($grade -isnot [int] -and $grade -isnot [long]) -or $grade -lt 0 -or $grade -gt 3) { $errors.Add(('invalid grade: ' + $row.file_id + '/' + $query)); continue }
    $counts[$grade]++
    $entry = $row.evidence.PSObject.Properties[$query]
    if ($grade -ge 2 -and $null -eq $entry) { $errors.Add(('missing evidence: ' + $row.file_id + '/' + $query)) }
    if ($null -ne $entry) {
      $evidenceCount++
      if ($grade -lt 2) { $errors.Add(('unexpected evidence: ' + $row.file_id + '/' + $query)) }
      $e = $entry.Value
      if ([string]::IsNullOrWhiteSpace($e.source_quote) -or -not $byId[$row.file_id].text.Contains($e.source_quote)) { $errors.Add(('quote not substring: ' + $row.file_id + '/' + $query)) }
      if ([string]::IsNullOrWhiteSpace($e.reason) -or [string]::IsNullOrWhiteSpace($e.limitation)) { $errors.Add(('empty reason or limitation: ' + $row.file_id + '/' + $query)) }
    }
  }
  foreach ($property in $row.evidence.PSObject.Properties) { if ($property.Name -notmatch '^KBT0(0[1-9]|1[0-9]|20)$') { $errors.Add(('invalid evidence key: ' + $row.file_id + '/' + $property.Name)) } }
}
foreach ($row in $sourceRows) { if (-not $seen.ContainsKey($row.file_id)) { $errors.Add(('missing source: ' + $row.file_id)) } }
$report = [ordered]@{ reviewer_id='p3'; source_documents=$sourceRows.Count; decision_documents=$decisionRows.Count; total_grades=($counts | Measure-Object -Sum).Sum; grade_counts=@{ '0'=$counts[0]; '1'=$counts[1]; '2'=$counts[2]; '3'=$counts[3] }; evidence_entries=$evidenceCount; checks_passed=($errors.Count -eq 0); errors=@($errors); human_approved=$false; annotation_origin='model_source_review' }
$report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath 'work\finrisk_evalset_20261015\annotations\part_3\validation.json' -Encoding UTF8
$report | ConvertTo-Json -Depth 5
if ($errors.Count -gt 0) { exit 1 }

