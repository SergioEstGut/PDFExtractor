from extractor_pdf.domain.entidades import PaginaPdf


class DetectorPaginaTecnicaRaloeCrono:
    def detectar(self, paginas: list[PaginaPdf]) -> PaginaPdf:
        candidatas = [(self._puntuar(pagina), pagina) for pagina in paginas]
        candidatas = [(puntuacion, pagina) for puntuacion, pagina in candidatas if puntuacion > 0]

        if not candidatas:
            raise ValueError("No se encontro la pagina tecnica de material.")

        return max(candidatas, key=lambda candidata: candidata[0])[1]

    @staticmethod
    def _puntuar(pagina: PaginaPdf) -> int:
        puntuacion = 0
        texto = pagina.texto

        senales_ponderadas = {
            "DETALLE DE MATERIAL": 5,
            "MANIOBRA CARLOS SILVA": 4,
            "Serie:": 3,
            "Normas:": 3,
            "Características:": 4,
            "CaracterÃ­sticas:": 4,
            "Tracción Eléctrica:": 5,
            "TracciÃ³n ElÃ©ctrica:": 5,
            "Puertas de Cabina Embarque 1:": 4,
            "Tensión Línea / Motor:": 3,
            "TensiÃ³n LÃ­nea / Motor:": 3,
        }

        for senal, peso in senales_ponderadas.items():
            if senal in texto:
                puntuacion += peso

        return puntuacion


class DetectorPaginaFosoHuidaOpcionesRaloeCrono:
    def detectar(self, paginas: list[PaginaPdf]) -> PaginaPdf:
        for pagina in paginas:
            tiene_gestion = (
                "Gestión foso / huida reducida:" in pagina.texto
                or "GestiÃ³n foso / huida reducida:" in pagina.texto
            )
            if tiene_gestion and "Limitador velocidad Cab:" in pagina.texto:
                return pagina
        raise ValueError("No se encontro la pagina de gestion foso / huida reducida.")


class DetectorPaginaPremontadaArmarioBotonerasRaloeCrono:
    def detectar(self, paginas: list[PaginaPdf]) -> PaginaPdf:
        for pagina in paginas:
            if "Premontada:" in pagina.texto and "Botonera Cabina:" in pagina.texto:
                return pagina
        raise ValueError("No se encontro la pagina de premontada / armario / botoneras.")







