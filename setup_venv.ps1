pip install venv
#pip install virtualenv
$dir = Split-Path -Path $PSScriptRoot
$venv_dir = [IO.Path]::Combine($dir, 'venv\personal_dashboard')

python -m venv $venv_dir
Invoke-Expression $venv_dir/Scripts/activate.ps1
pip install -r $PSScriptRoot/requirements.txt