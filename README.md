# ExtractorPDF

API FastAPI para extraer datos estructurados desde PDFs de pedidos.

La arquitectura separa:

- `domain`: modelos y contratos puros del negocio.
- `application`: casos de uso y orquestacion.
- `infrastructure`: adaptadores concretos para PDF, OCR y modelos.
- `interfaces`: entrada/salida de la aplicacion, empezando por FastAPI.

