# VI: ExtraerDataDesdePath.vi

Objetivo: enviar a la API el path de un PDF accesible por el servidor y recibir el JSON plano devuelto por `/extract/data`.

## Conector

Entradas:

- `api_url` string
  - Valor recomendado: `http://192.168.1.118:8001/extract/data`
- `pdf_path` path/string
  - Debe ser una ruta accesible desde la maquina donde corre la API.
  - Si LabVIEW esta en otra maquina, usar ruta compartida, por ejemplo `\\SERVIDOR\Pedidos\654144.pdf`.
- `profile_id` string
  - Valor por defecto: `raloe_crono`
- `timeout_ms` numeric
  - Valor recomendado: `300000`

Salidas:

- `json_response` string
- `status_code` I32
- `error out` cluster

## Flujo del diagrama

1. Convertir `pdf_path` a string si entra como tipo Path.
2. Construir body `application/x-www-form-urlencoded`:

   ```text
   profile_id=raloe_crono&pdf_path=<pdf_path_url_encoded>
   ```

3. Abrir cliente HTTP.
4. Configurar cabecera:

   ```text
   Content-Type: application/x-www-form-urlencoded
   ```

5. Ejecutar POST contra `api_url`.
6. Leer:
   - status code
   - response body como string
7. Cerrar cliente HTTP.
8. Si `status_code` no esta entre 200 y 299, activar `error out`.

## Importante

El campo `pdf_path` debe ir URL encoded. Como minimo hay que codificar:

- espacio -> `%20` o `+`
- `\` -> `%5C`
- `:` -> `%3A`
- `&` -> `%26`
- `=` -> `%3D`
- `%` -> `%25`

Ejemplo de body:

```text
profile_id=raloe_crono&pdf_path=D%3A%5CProyectos%20Python%5CExtractorPDF%5Cpdfs%5C654144.pdf
```

## Respuesta esperada

La API devuelve un JSON plano:

```json
{
  "general.Serie": "CRONO",
  "Normas.Norma_81_73_txt": "",
  "Observaciones": "Texto...\nCampo extra: ...\nNota extra: ..."
}
```

## Conversion posterior a array 2D

Si quieres convertir el JSON a array 2D en LabVIEW:

1. Parsear el JSON como objeto/diccionario.
2. Obtener lista de claves.
3. Para cada clave:
   - columna 0 = clave
   - columna 1 = valor como string
4. Construir array 2D string.

Recomendacion: usar JSONtext para LabVIEW si esta disponible, porque maneja objetos con claves dinamicas mejor que clusters fijos.
