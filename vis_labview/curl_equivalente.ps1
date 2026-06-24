$apiUrl = "http://192.168.1.118:8001/extract/data"
$pdfPath = "D:\Proyectos Python\ExtractorPDF\pdfs\654144.pdf"

$body = @{
    profile_id = "raloe_crono"
    pdf_path = $pdfPath
}

Invoke-RestMethod -Method Post -Uri $apiUrl -Body $body -ContentType "application/x-www-form-urlencoded"
