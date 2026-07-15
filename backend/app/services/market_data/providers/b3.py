from __future__ import annotations

from app.core.config import get_settings


class B3PublicDataProvider:
    name = "b3"

    def __init__(self) -> None:
        self.settings = get_settings()

    def get_available_sources(self) -> list[dict]:
        return [
            {
                "name": "Instrumentos listados e informacoes publicas",
                "baseUrl": self.settings.b3_base_url,
                "status": "preparado",
                "notes": "Conector reservado para sincronizacao de cadastro, classe e metadados de ativos.",
            }
        ]
