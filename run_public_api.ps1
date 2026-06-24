cd "D:\Proyectos Python\ExtractorPDF"

.\.venv\Scripts\uvicorn.exe `
  extractor_pdf.interfaces.api.main:app `
  --host 0.0.0.0 `
  --port 8001 `
  --reload