$env:PYTHONPATH = "E:\ProyectosPython\ExtractorPDF\.venv\Lib\site-packages;E:\ProyectosPython\ExtractorPDF\src"

& "C:\Users\Sergio Esteban\AppData\Local\Programs\Python\Python310\python.exe" `
  -m pytest `
  -m "ocr" `
  -q
