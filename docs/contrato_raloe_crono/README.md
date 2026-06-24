# Plantillas de contrato Raloe-CRONO

Esta carpeta divide el contrato por secciones para que sea mas facil revisar y completar la especificacion de campos.

Cada archivo de `secciones/` parte del contrato base actual y usa esta forma:

```json
{
  "nombre": "Nombre_del_campo",
  "tipo": "pendiente",
  "valor_defecto": "",
  "aliases": [],
  "reglas": {}
}
```

## Tipos previstos

Check simple:

```json
{
  "nombre": "Cableado_LSF",
  "tipo": "check_simple",
  "valor_defecto": "No",
  "aliases": [],
  "reglas": {
    "valor_marcado": "Si",
    "valor_no_marcado": "No"
  }
}
```

Check con valor asociado:

Se representa siempre con dos campos: uno para el estado del check y otro para el
valor escrito al lado. El valor asociado suele usar el sufijo `_txt`, aunque el
tipo puede ser `texto`, `int` o `double` para indicar como normalizarlo.

```json
{
  "nombre": "Leva_electrica_op1",
  "tipo": "check_simple",
  "valor_defecto": "No",
  "aliases": [],
  "reglas": {
    "valor_marcado": "Si",
    "valor_no_marcado": "No"
  }
}
```

```json
{
  "nombre": "Leva_electrica_op1_txt",
  "tipo": "double",
  "valor_defecto": "",
  "aliases": [],
  "reglas": {
    "infiere_check_marcado": "Leva_electrica_op1",
    "extraer_solo_numero": true
  }
}
```

Si el campo asociado tiene un valor leido y normalizado, el check indicado por
`infiere_check_marcado` se considera marcado. La ausencia de valor no implica
que el check este desmarcado.

Texto simple:

```json
{
  "nombre": "Fabricante_motor",
  "tipo": "texto",
  "valor_defecto": "",
  "aliases": [],
  "reglas": {}
}
```
