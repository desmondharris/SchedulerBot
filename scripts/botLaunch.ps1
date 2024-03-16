$scripts = $PSScriptRoot
cd $scripts

Start-Process powershell -ArgumentList "-noexit", ".\..\venv\Scripts\Activate; cd ..; python -m src.PersistentBot 0"