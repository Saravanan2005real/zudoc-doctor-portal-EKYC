$target = "c:\Users\DINESH\Desktop\eKYC\eye tracker"
if (Test-Path -LiteralPath $target) {
  try {
    Remove-Item -LiteralPath $target -Recurse -Force -ErrorAction Stop
    Write-Host "Deleted eye tracker"
  } catch {
    Write-Host "Still locked. Close any terminal whose cwd is inside 'eye tracker', then re-run this script."
    Write-Host $_
  }
} else {
  Write-Host "Already removed"
}
