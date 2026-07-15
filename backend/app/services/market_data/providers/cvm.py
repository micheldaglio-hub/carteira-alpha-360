from __future__ import annotations

from app.core.config import get_settings


class CvmPublicDataProvider:
    name = "cvm"

    def __init__(self) -> None:
        self.settings = get_settings()

    def get_available_sources(self) -> list[dict]:
        return [
            {
                "name": "Dados cadastrais e demonstracoes",
                "baseUrl": self.settings.cvm_base_url,
                "status": "preparado",
                "notes": "Conector reservado para baixar e normalizar arquivos publicos da CVM em jobs assincronos.",
            }
        ]
