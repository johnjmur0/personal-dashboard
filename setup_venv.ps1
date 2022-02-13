pip install venv
pip install virtualenv
$venv_dir = [IO.Path]::Combine($PSScriptRoot, '/venv/personal_dashboard')
python -m venv $venv_dir

Invoke-Expression $venv_dir/Scripts/activate.ps1

pip install -r $PSScriptRoot/requirements.txt