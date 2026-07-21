param(
    [string]$DistDir = (Join-Path $PSScriptRoot '..\..\dist\TypofixCN'),
    [switch]$Offline,
    [int]$Port = 8000
)

$ErrorActionPreference = 'Stop'
$DistDir = [IO.Path]::GetFullPath($DistDir)
$Exe = Join-Path $DistDir 'TypofixCN.exe'
$Log = Join-Path $DistDir 'logs\typofix.log'
$BaseUrl = "http://127.0.0.1:$Port"
$Process = $null

function New-SmokeDocx([string]$Path) {
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $parent = Split-Path -Parent $Path
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    if (Test-Path -LiteralPath $Path) { Remove-Item -LiteralPath $Path -Force }
    $archive = [System.IO.Compression.ZipFile]::Open($Path, [System.IO.Compression.ZipArchiveMode]::Create)
    try {
        $entries = @{
            '[Content_Types].xml' = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'
            '_rels/.rels' = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'
            'word/document.xml' = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>今天新情很好</w:t></w:r></w:p><w:sectPr/></w:body></w:document>'
        }
        foreach ($name in $entries.Keys) {
            $entry = $archive.CreateEntry($name)
            $stream = $entry.Open()
            try {
                $bytes = [Text.Encoding]::UTF8.GetBytes($entries[$name])
                $stream.Write($bytes, 0, $bytes.Length)
            } finally { $stream.Dispose() }
        }
    } finally { $archive.Dispose() }
}

function Send-MultipartDocx([string]$Url, [string]$Path) {
    $boundary = '----TypofixSmoke' + [Guid]::NewGuid().ToString('N')
    $request = [Net.HttpWebRequest]::Create($Url)
    $request.Method = 'POST'
    $request.ContentType = "multipart/form-data; boundary=$boundary"
    $request.Timeout = 30000
    $stream = $request.GetRequestStream()
    try {
        $head = "--$boundary`r`nContent-Disposition: form-data; name=`"files`"; filename=`"smoke.docx`"`r`nContent-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document`r`n`r`n"
        $headBytes = [Text.Encoding]::UTF8.GetBytes($head)
        $stream.Write($headBytes, 0, $headBytes.Length)
        $data = [IO.File]::ReadAllBytes($Path)
        $stream.Write($data, 0, $data.Length)
        $tailBytes = [Text.Encoding]::UTF8.GetBytes("`r`n--$boundary--`r`n")
        $stream.Write($tailBytes, 0, $tailBytes.Length)
    } finally { $stream.Dispose() }
    $response = $request.GetResponse()
    try {
        $reader = New-Object IO.StreamReader($response.GetResponseStream())
        try { return ($reader.ReadToEnd() | ConvertFrom-Json) } finally { $reader.Dispose() }
    } finally { $response.Dispose() }
}

function Resolve-BundledPath([string]$RelativePath) {
    $direct = Join-Path $DistDir $RelativePath
    if (Test-Path -LiteralPath $direct) { return $direct }
    $internal = Join-Path $DistDir (Join-Path '_internal' $RelativePath)
    if (Test-Path -LiteralPath $internal) { return $internal }
    return $direct
}

try {
    if (!(Test-Path -LiteralPath $Exe)) { throw "Missing executable: $Exe" }
    if (!(Test-Path -LiteralPath (Resolve-BundledPath 'frontend\dist\index.html'))) { throw 'Missing bundled frontend' }
    if (!(Test-Path -LiteralPath (Resolve-BundledPath 'data\models\macbert4csc-base-chinese\onnx\model.onnx'))) { throw 'Missing bundled ONNX model' }

    $smokeDir = Join-Path $env:TEMP 'typofix-win7-smoke'
    $docx = Join-Path $smokeDir 'smoke.docx'
    New-SmokeDocx $docx
    $Process = Start-Process -FilePath $Exe -WorkingDirectory $DistDir -WindowStyle Hidden -PassThru
    $health = $null
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Milliseconds 500
        try { $health = Invoke-RestMethod "$BaseUrl/api/v1/health" -TimeoutSec 3; break } catch {}
    }
    if ($null -eq $health -or $health.status -ne 'ok') { throw 'Frozen executable did not become healthy within 30 seconds' }

    $job = Send-MultipartDocx "$BaseUrl/api/v1/jobs" $docx
    if ([string]::IsNullOrWhiteSpace($job.job_id)) { throw 'Upload did not return a job id' }
    $status = $null
    for ($i = 0; $i -lt 120; $i++) {
        Start-Sleep -Milliseconds 500
        $status = Invoke-RestMethod "$BaseUrl/api/v1/jobs/$($job.job_id)"
        if ($status.status -like 'completed*' -or $status.status -eq 'failed') { break }
    }
    if ($status.status -notlike 'completed*') { throw "Release smoke job failed: $($status.error)" }
    $report = Invoke-RestMethod "$BaseUrl/api/v1/jobs/$($job.job_id)/report.json"
    $html = Invoke-WebRequest "$BaseUrl/api/v1/jobs/$($job.job_id)/report.html" -UseBasicParsing
    if ($report.schema_version -ne 1 -or $html.StatusCode -ne 200) { throw 'Report endpoints did not return a valid report' }
    if ($Offline -and (Test-Path -LiteralPath $Log)) {
        $logText = Get-Content -LiteralPath $Log -Raw
        if ($logText -match '(?i)(huggingface|snapshot_download|https?://(?!127\.0\.0\.1|localhost))') {
            throw 'Offline smoke found a model-download or external-network access in the log'
        }
    }
    Write-Host "Release smoke passed: $($job.job_id)"
} finally {
    if ($null -ne $Process -and !$Process.HasExited) { Stop-Process -Id $Process.Id -Force }
}
