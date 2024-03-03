Start-Process powershell -ArgumentList  "cd C:\Users\desmo\PycharmProjects\Scheduler\src\apps; python -m http.server 80"

Start-Process powershell -ArgumentList "-noexit", "cd C:\Users\desmo\PycharmProjects\Scheduler\src\apps; .\ngrok http --domain=regularly-unbiased-stud.ngrok-free.app 80"