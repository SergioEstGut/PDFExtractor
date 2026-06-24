from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracion(BaseSettings):
    nombre_app: str = "ExtractorPDF"
    cliente_por_defecto: str = "cliente_base"
    min_caracteres_texto_pagina: int = 40
    motor_ocr: str = "none"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


configuracion = Configuracion()







