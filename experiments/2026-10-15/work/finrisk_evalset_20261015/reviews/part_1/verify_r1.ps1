$ErrorActionPreference = 'Stop'
$taskRoot = 'C:\Users\11051\Documents\Codex\2026-10-09\c-users-11051-desktop-agent-ai'
$inputPath = Join-Path $taskRoot 'outputs\FinRisk_可用测试集_v1_20261015\annotation_inputs\part_1.jsonl'
$queryPath = Join-Path $taskRoot 'outputs\FinRisk_可用测试集_v1_20261015\query_specs.jsonl'
$decisionPath = Join-Path $taskRoot 'work\finrisk_evalset_20261015\reviews\part_1\decisions.jsonl'
$reportPath = Join-Path $taskRoot 'work\finrisk_evalset_20261015\reviews\part_1\verification_r1.json'
$sources = @(Get-Content -LiteralPath $inputPath -Encoding UTF8 | ForEach-Object { $_ | ConvertFrom-Json })
$queries = @(Get-Content -LiteralPath $queryPath -Encoding UTF8 | ForEach-Object { $_ | ConvertFrom-Json })
$decisions = @(Get-Content -LiteralPath $decisionPath -Encoding UTF8 | ForEach-Object { $_ | ConvertFrom-Json })
$sourceById = @{}
foreach ($source in $sources) { $sourceById[$source.file_id] = $source }
$issues = [System.Collections.Generic.List[string]]::new()
if ($sources.Count -ne 34) { $issues.Add('source_count_not_34') }
if ($decisions.Count -ne 34) { $issues.Add('decision_count_not_34') }
if ($queries.Count -ne 20) { $issues.Add('query_count_not_20') }
$seen = @{}
$gradeCounts = [ordered]@{ '0' = 0; '1' = 0; '2' = 0; '3' = 0 }
$perQuery = [ordered]@{}
foreach ($query in $queries) { $perQuery[$query.query_id] = [ordered]@{ '0' = 0; '1' = 0; '2' = 0; '3' = 0 } }
$checkedQuotes = 0
foreach ($decision in $decisions) {
    $id = [string]$decision.file_id
    if ($seen.ContainsKey($id)) { $issues.Add("duplicate_file_id:$id") }
    $seen[$id] = $true
    if (-not $sourceById.ContainsKey($id)) { $issues.Add("unknown_file_id:$id"); continue }
    if (@($decision.grades).Count -ne 20) { $issues.Add("grade_count:$id") }
    if ($decision.all20_queries_reviewed -ne $true) { $issues.Add("not_all20_reviewed:$id") }
    if ($decision.origin -cne 'model_source_review') { $issues.Add("wrong_origin:$id") }
    if ($decision.reviewer_id -cne 'r1') { $issues.Add("wrong_reviewer:$id") }
    if ($decision.human_approved -ne $false -or $decision.human_approved -isnot [bool]) { $issues.Add("false_human_status_missing:$id") }
    if ([string]::IsNullOrWhiteSpace([string]$decision.document_mechanism_summary)) { $issues.Add("missing_summary:$id") }
    for ($i = 0; $i -lt @($decision.grades).Count; $i++) {
        $grade = $decision.grades[$i]
        $queryId = 'KBT{0:D3}' -f ($i + 1)
        if (($grade -isnot [int] -and $grade -isnot [long]) -or $grade -lt 0 -or $grade -gt 3) { $issues.Add("invalid_integer_grade:${id}:$queryId"); continue }
        $gradeCounts[[string]$grade]++
        $perQuery[$queryId][[string]$grade]++
        if ($grade -ge 2) {
            $evidence = $decision.evidence.$queryId
            if ($null -eq $evidence) { $issues.Add("missing_evidence:${id}:$queryId"); continue }
            foreach ($key in @('source_quote', 'reason', 'limitation')) {
                if ([string]::IsNullOrWhiteSpace([string]$evidence.$key)) { $issues.Add("empty_${key}:${id}:$queryId") }
            }
            $quote = [string]$evidence.source_quote
            if (-not $sourceById[$id].text.Contains($quote)) { $issues.Add("quote_not_in_source:${id}:$queryId") }
            $checkedQuotes++
        }
    }
    foreach ($property in $decision.evidence.PSObject.Properties) {
        if ($property.Name -notmatch '^KBT(00[1-9]|01[0-9]|020)$') { $issues.Add("invalid_evidence_query:${id}:$($property.Name)") }
    }
}
foreach ($source in $sources) { if (-not $seen.ContainsKey($source.file_id)) { $issues.Add("missing_source:$($source.file_id)") } }
$report = [ordered]@{
    reviewer_id = 'r1'
    checked_at_utc = [DateTime]::UtcNow.ToString('o')
    source_count = $sources.Count
    decision_count = $decisions.Count
    queries_per_document = 20
    explicit_grades_count = ($gradeCounts.Values | Measure-Object -Sum).Sum
    evidence_quotes_checked = $checkedQuotes
    grade_distribution = $gradeCounts
    per_query_distribution = $perQuery
    human_approved_true_count = @($decisions | Where-Object { $_.human_approved -eq $true }).Count
    all20_queries_reviewed_true_count = @($decisions | Where-Object { $_.all20_queries_reviewed -eq $true }).Count
    source_sha256 = (Get-FileHash -LiteralPath $inputPath -Algorithm SHA256).Hash
    decisions_sha256 = (Get-FileHash -LiteralPath $decisionPath -Algorithm SHA256).Hash
    passed = ($issues.Count -eq 0)
    issues = @($issues)
}
$report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $reportPath -Encoding UTF8
$report | ConvertTo-Json -Depth 10
if ($issues.Count -gt 0) { exit 1 }
