$scripts = $PSScriptRoot
cd $scripts

Start-Process powershell -ArgumentList "-noexit", ".\ngrok http --domain=regularly-unbiased-stud.ngrok-free.app 80"
Start-Process powershell -ArgumentList "-noexit", "cd .\..\apps; python -m http.server 80"
Start-Process powershell -ArgumentList "-noexit", ".\..\venv\Scripts\Activate; cd ..; python -m src.PersistentBot 0"