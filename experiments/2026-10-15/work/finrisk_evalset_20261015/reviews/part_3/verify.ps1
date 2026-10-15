$ErrorActionPreference = 'Stop'
$inputPath = 'C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/outputs/FinRisk_可用测试集_v1_20261015/annotation_inputs/part_3.jsonl'
$decisionsPath = 'C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/work/finrisk_evalset_20261015/reviews/part_3/decisions.jsonl'
$verificationPath = 'C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/work/finrisk_evalset_20261015/reviews/part_3/verification.json'
$sources = @(Get-Content -LiteralPath $inputPath -Encoding UTF8 | ForEach-Object { $_ | ConvertFrom-Json })
$decisions = @(Get-Content -LiteralPath $decisionsPath -Encoding UTF8 | ForEach-Object { $_ | ConvertFrom-Json })
$sourceMap = @{}
foreach ($source in $sources) { $sourceMap[$source.file_id] = $source.text }
$seen = @{}
$errorsFound = [System.Collections.Generic.List[string]]::new()
$distribution = [ordered]@{'0'=0;'1'=0;'2'=0;'3'=0}
$quoteCount = 0
$perQuery = @()
if ($sources.Count -ne 33 -or $decisions.Count -ne 33) { $errorsFound.Add('Expected 33 input documents and 33 decision records.') }
foreach ($decision in $decisions) {
    if ($seen.ContainsKey($decision.file_id)) { $errorsFound.Add("Duplicate file_id: $($decision.file_id)") }
    $seen[$decision.file_id] = $true
    if (-not $sourceMap.ContainsKey($decision.file_id)) { $errorsFound.Add("Unknown file_id: $($decision.file_id)") }
    if (@($decision.grades).Count -ne 20) { $errorsFound.Add("Invalid grade count: $($decision.file_id)") }
    if ($decision.all20_queries_reviewed -ne $true) { $errorsFound.Add("Review completeness flag invalid: $($decision.file_id)") }
    if ($decision.origin -cne 'model_source_review' -or $decision.reviewer_id -cne 'r3' -or $decision.human_approved -ne $false) { $errorsFound.Add("Origin, reviewer or approval flag invalid: $($decision.file_id)") }
    if ([string]::IsNullOrWhiteSpace($decision.document_mechanism_summary)) { $errorsFound.Add("Missing mechanism summary: $($decision.file_id)") }
    for ($index = 0; $index -lt $decision.grades.Count; $index++) {
        $grade = $decision.grades[$index]
        $queryId = 'KBT{0:D3}' -f ($index + 1)
        if (($grade -isnot [int] -and $grade -isnot [long]) -or $grade -lt 0 -or $grade -gt 3) { $errorsFound.Add("Invalid integer grade: $($decision.file_id)/$queryId"); continue }
        $distribution[[string]$grade]++
        $item = $decision.evidence.PSObject.Properties[$queryId]
        if ($grade -ge 2 -and $null -eq $item) { $errorsFound.Add("Missing evidence: $($decision.file_id)/$queryId") }
    }
    foreach ($item in $decision.evidence.PSObject.Properties) {
        $quoteCount++
        $evidence = $item.Value
        if ($item.Name -notmatch '^KBT0(0[1-9]|1[0-9]|20)$') { $errorsFound.Add("Invalid evidence query ID: $($decision.file_id)/$($item.Name)") }
        if ([string]::IsNullOrWhiteSpace($evidence.source_quote) -or -not $sourceMap[$decision.file_id].Contains([string]$evidence.source_quote, [StringComparison]::Ordinal)) { $errorsFound.Add("Quote not a continuous source substring: $($decision.file_id)/$($item.Name)") }
        if ([string]::IsNullOrWhiteSpace($evidence.reason) -or [string]::IsNullOrWhiteSpace($evidence.limitation)) { $errorsFound.Add("Missing evidence explanation: $($decision.file_id)/$($item.Name)") }
    }
}
foreach ($source in $sources) { if (-not $seen.ContainsKey($source.file_id)) { $errorsFound.Add("Unreviewed source ID: $($source.file_id)") } }
for ($index = 0; $index -lt 20; $index++) {
    $counts = [ordered]@{'0'=0;'1'=0;'2'=0;'3'=0}
    foreach ($decision in $decisions) { $counts[[string]$decision.grades[$index]]++ }
    $perQuery += [ordered]@{query_id=('KBT{0:D3}' -f ($index + 1)); grade_distribution=$counts}
}
$result = [ordered]@{
    reviewer_id='r3'
    source_file=$inputPath
    decisions_file=$decisionsPath
    input_document_count=$sources.Count
    output_document_count=$decisions.Count
    explicit_integer_grade_count=($distribution.Values | Measure-Object -Sum).Sum
    grade_distribution=$distribution
    evidence_quote_count=$quoteCount
    quotes_are_exact_continuous_substrings=($errorsFound.Count -eq 0)
    all20_queries_reviewed_flags_valid=(@($decisions | Where-Object { $_.all20_queries_reviewed -ne $true }).Count -eq 0)
    all_human_approved_false=(@($decisions | Where-Object { $_.human_approved -ne $false }).Count -eq 0)
    semantic_grades_assigned_by_model=$true
    program_role='serialization and mechanical validation only; no inferred grades'
    errors=@($errorsFound.ToArray())
    per_query=$perQuery
    passed=($errorsFound.Count -eq 0)
}
$result | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $verificationPath -Encoding UTF8
[pscustomobject]$result | Select-Object reviewer_id,input_document_count,output_document_count,explicit_integer_grade_count,grade_distribution,evidence_quote_count,passed,errors | ConvertTo-Json -Depth 5
if ($errorsFound.Count -gt 0) { exit 1 }
