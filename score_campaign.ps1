param(
    [datetime]$AsOf = [datetime]::Today
)

$ErrorActionPreference = 'Stop'
$outputDirectory = Join-Path $PSScriptRoot 'output'
$reviewPath = Join-Path $outputDirectory 'icp_reviews.local.json'
if (-not (Test-Path -LiteralPath $reviewPath -PathType Leaf)) {
    throw 'Missing output/icp_reviews.local.json. Copy and populate icp_reviews.example.json.'
}
$reviewData = Get-Content -Raw -LiteralPath $reviewPath | ConvertFrom-Json -AsHashtable
$reliabilityByDomain = $reviewData['reliability_by_domain']
$reviews = @{}
foreach ($entry in $reviewData['reviews']) { $reviews[$entry[0]] = $entry }

# Identify each input by its columns, newest first. Skip outputs from previous runs.
$inputs = @(Get-ChildItem -LiteralPath $outputDirectory -Filter '*.csv' |
    Where-Object Name -notin @('scored_companies.csv', 'scored_contacts.csv', 'priority_accounts.csv') |
    Sort-Object LastWriteTimeUtc -Descending | ForEach-Object {
        $values = @(Import-Csv -LiteralPath $_.FullName)
        if ($values.Count) { [pscustomobject]@{ Name=$_.Name; Rows=$values; Columns=@($values[0].PSObject.Properties.Name) } }
    })
$companyFile = $inputs | Where-Object { 'estimated_employee_range' -in $_.Columns -and @($_.Rows | Where-Object qualification_status -ne 'Qualified').Count -eq 0 } | Select-Object -First 1
$roleFile = $inputs | Where-Object { 'role_evidence' -in $_.Columns -and 'priority_tier' -in $_.Columns } | Select-Object -First 1
$emailFile = $inputs | Where-Object { 'business_email' -in $_.Columns -and 'phone_number' -notin $_.Columns } | Select-Object -First 1
$phoneFile = $inputs | Where-Object { 'phone_number' -in $_.Columns -and 'business_email' -in $_.Columns } | Select-Object -First 1
if (-not ($companyFile -and $roleFile -and $emailFile -and $phoneFile)) { throw 'Could not locate all four source schemas' }

function Get-ProfileKey([string]$Url) {
    if ($Url -match '^https?://(?:[a-z0-9-]+\.)?linkedin\.com/in/([^/?#]+)') {
        return [uri]::UnescapeDataString($Matches[1]).ToLowerInvariant()
    }
    return ''
}

$companies = @{}
foreach ($row in $companyFile.Rows) {
    if ($companies.ContainsKey($row.website_domain)) { throw 'Duplicate qualified domain' }
    $companies[$row.website_domain] = $row
}

$contactsByKey = @{}
foreach ($row in @($roleFile.Rows) + @($emailFile.Rows) + @($phoneFile.Rows)) {
    if (-not $row.full_name) { continue }
    $profile = Get-ProfileKey $row.linkedin_profile_url
    if (-not $profile -or -not $companies.ContainsKey($row.company_domain)) { throw 'Named contact could not be linked by profile and qualified domain' }
    if (-not $contactsByKey.ContainsKey($profile)) { $contactsByKey[$profile] = $row }
    elseif ($contactsByKey[$profile].company_domain -ne $row.company_domain) { throw 'Conflicting company domains for one contact' }
}
$emailByKey = @{}
foreach ($row in $emailFile.Rows) { $emailByKey[(Get-ProfileKey $row.linkedin_profile_url)] = $row }
$phoneByKey = @{}
foreach ($row in $phoneFile.Rows) { $phoneByKey[(Get-ProfileKey $row.linkedin_profile_url)] = $row }

# ICP is 10 for US headquarters, 10 for a range wholly inside 20–250, and 5 for B2B software/AI/tech.
# Evidence reviews below are fixed judgments based on the saved Exa evidence.
# Freshness is 4 points at <=180 days, 3 at <=365, 2 at <=730, otherwise 1. Undated earns 0.
# Reliability is 6 for a specific first-party launch, technical doc, benchmark, or research result;
# 5 for a hiring post or expansion announcement; 4 for a product or workflow capability page.
$scored = @(foreach ($company in $companyFile.Rows) {
    $domain = $company.website_domain
    $assessment = $reviews[$domain]
    if (-not $assessment -or $company.supporting_source_url -notmatch '^https://') { throw "Missing reviewed source for $domain" }
    $range = [regex]::Match($company.estimated_employee_range,'^(\d+)-(\d+)$')
    $sizeFit = $range.Success -and [int]$range.Groups[1].Value -ge 20 -and [int]$range.Groups[2].Value -le 250
    $usFit = $company.headquarters_country_code -eq 'US'
    $industryFit = $company.industry -eq 'Software' -or ($company.industry -eq 'Media & Internet' -and $domain -in $reviewData['media_industry_fit_domains'])
    $industryBasis = if ($company.industry -eq 'Media & Internet' -and $industryFit) { 'Technology fit confirmed by the AI infrastructure product description and source.' } else { 'B2B software or AI product documented in the qualified company record and source.' }
    $icp = 10*[int]$usFit + 10*[int]$sizeFit + 5*[int]$industryFit
    if (-not $reliabilityByDomain.ContainsKey($domain)) { throw "Missing evidence reliability for $domain" }
    $reliability = [int]$reliabilityByDomain[$domain]
    $freshness = 0
    $ageDays = ''
    if ($company.signal_date) {
        $date = [datetime]::ParseExact($company.signal_date,'yyyy-MM-dd',[cultureinfo]::InvariantCulture)
        $ageDays = ($AsOf.Date - $date.Date).Days
        $freshness = if ($ageDays -lt 0) {0} elseif ($ageDays -le 180) {4} elseif ($ageDays -le 365) {3} elseif ($ageDays -le 730) {2} else {1}
    }
    $score = $icp + [int]$assessment[1] + [int]$assessment[2] + [int]$assessment[3] + $reliability + $freshness
    $tier = if ($score -ge 80) {'Tier 1'} elseif ($score -ge 60) {'Tier 2'} else {'Tier 3'}
    $roles = @($contactsByKey.Values | Where-Object { $_.company_domain -eq $domain -and $_.verification_status -like 'Verified*' })
    $missing = @($assessment[7])
    if (-not $company.signal_date) { $missing += 'Signal date is absent from the source CSV' }
    if (-not $roles.Count) { $missing += 'No verified decision-maker in current files' }
    [pscustomobject][ordered]@{
      rank=0; company_name=$company.company_name; website_domain=$domain; score=$score; priority_tier=$tier
      icp_fit_25=$icp; ai_infrastructure_relevance_20=$assessment[1]; buying_signals_25=$assessment[2]
      conifer_pain_relevance_20=$assessment[3]; freshness_reliability_10=$freshness+$reliability
      freshness_4=$freshness; source_reliability_6=$reliability; signal_age_days=$ageDays
      headquarters_country=$company.headquarters_country; observed_employee_count=$company.observed_employee_count
      estimated_employee_range=$company.estimated_employee_range; industry=$company.industry; industry_basis=$industryBasis
      original_buying_signal=$company.buying_signal; signal_categories=$assessment[4]; evidence_status='First-party evidence recorded by Exa; purchasing intent unknown'
      confirmed_evidence=$assessment[5]; conifer_fit_inference=$assessment[6]; evidence_url=$company.supporting_source_url
      signal_date=$company.signal_date; missing_information=($missing -join ' | '); verified_contact_count=$roles.Count
      score_explanation="$($assessment[5]) $($assessment[6])"
      conifer_product_sources='https://www.conifer.build/gateway/ | https://www.conifer.build/router/'
      as_of=$AsOf.ToString('yyyy-MM-dd'); source_file=$companyFile.Name
    }
})
$ranked = @($scored | Sort-Object @{e='score';Descending=$true}, @{e='buying_signals_25';Descending=$true}, @{e='freshness_reliability_10';Descending=$true}, website_domain)
for ($i=0; $i -lt $ranked.Count; $i++) { $ranked[$i].rank = $i+1 }
$ranks = @{}
foreach ($row in $ranked) { $ranks[$row.website_domain] = $row }

$contactResults = @(foreach ($key in $contactsByKey.Keys) {
    $role = $contactsByKey[$key]
    $email = $emailByKey[$key]
    $phone = $phoneByKey[$key]
    $account = $ranks[$role.company_domain]
    $relevance = switch ([string]$role.priority_tier) {
        '1' {'Direct AI infrastructure ownership indicated by title'}
        '2' {if ($role.current_job_title -match '\bField CTO\b') {'Field CTO; technical influencer, internal infrastructure ownership unconfirmed'} else {'CTO; relevant technical leadership, budget ownership unconfirmed'}}
        '3' {'Engineering leadership; model infrastructure ownership unconfirmed'}
        '4' {'IT leadership; AI infrastructure scope unconfirmed'}
        '5' {'IT ownership; AI infrastructure scope unconfirmed'}
        default {'Role relevance needs review'}
    }
    $gaps = @()
    if (-not $email.business_email -and -not $phone.business_email) {$gaps += 'Business email unavailable'}
    if (-not $phone.phone_number) {$gaps += 'Phone unavailable or not tested'}
    if ($phone.phone_number -and $phone.phone_verification_status -match 'no separate') {$gaps += 'No separate phone verification supplied'}
    if ($email.email_review_status -like 'Review*') {$gaps += $email.email_review_status}
    [pscustomobject][ordered]@{
      account_rank=$account.rank; account_score=$account.score; account_tier=$account.priority_tier
      full_name=$role.full_name; job_title=$role.current_job_title; company=$role.company_name; company_domain=$role.company_domain
      linkedin_url=$role.linkedin_profile_url; decision_maker_relevance=$relevance; role_verification_status=$role.verification_status
      role_evidence=$role.role_evidence; role_evidence_url=$role.evidence_url
      business_email=($email.business_email ?? $phone.business_email); email_verification_status=($email.provider_email_status ?? $phone.provider_email_status)
      email_review_status=($email.email_review_status ?? $phone.email_review_status); phone_number=$phone.phone_number
      phone_verification_status=$phone.phone_verification_status; phone_provider=$phone.phone_provider
      original_buying_signal=$account.original_buying_signal; signal_evidence_url=$account.evidence_url; signal_date=$account.signal_date
      missing_information=($gaps -join ' | '); role_source_file=$roleFile.Name; email_source_file=$emailFile.Name; phone_source_file=$phoneFile.Name
    }
})
$contactResults = @($contactResults | Sort-Object account_rank,full_name)
$priority = @($ranked | Select-Object -First 5 | ForEach-Object {
    $account = $_
    $names = @($contactResults | Where-Object {$_.company_domain -eq $account.website_domain -and $_.role_verification_status -like 'Verified*'} |
        ForEach-Object {"$($_.full_name) ($($_.job_title))"})
    $account | Select-Object *,@{n='verified_decision_makers';e={$names -join ' | '}}
})
if ($ranked.Count -ne $companies.Count -or $contactResults.Count -ne $contactsByKey.Count) { throw 'Source coverage check failed' }
$ranked | Export-Csv -LiteralPath (Join-Path $outputDirectory 'scored_companies.csv') -NoTypeInformation -Encoding utf8
$contactResults | Export-Csv -LiteralPath (Join-Path $outputDirectory 'scored_contacts.csv') -NoTypeInformation -Encoding utf8
$priority | Export-Csv -LiteralPath (Join-Path $outputDirectory 'priority_accounts.csv') -NoTypeInformation -Encoding utf8
[pscustomobject]@{ Companies=$ranked.Count; Contacts=$contactResults.Count; TierCounts=@($ranked | Group-Object priority_tier | Select-Object Name,Count) } | ConvertTo-Json -Compress
$ranked | Select-Object rank,company_name,score,priority_tier,verified_contact_count | Format-Table -AutoSize
$priority | Select-Object company_name,verified_decision_makers,missing_information | ConvertTo-Json -Compress
