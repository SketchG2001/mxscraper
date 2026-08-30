"""Application settings loaded from environment / .env file."""

from __future__ import annotations

try:
    from pydantic_settings import BaseSettings

    _PYDANTIC_V2 = True
except ImportError:  # Android: pydantic 1.10 (no pydantic-core wheel)
    from pydantic import BaseSettings

    _PYDANTIC_V2 = False


class Settings(BaseSettings):
    # Auth0
    auth0_domain: str = ""
    auth0_audience: str = ""
    auth0_algorithms: str = "RS256"

    # Server
    port: int = 8000
    proxy_port: int = 8513
    # HLS proxy bind. Web default is all interfaces; Android bootstrap sets 127.0.0.1.
    proxy_bind_host: str = "0.0.0.0"
    # Set by the Android uvicorn bootstrap (ANDROID_RUNTIME=1). Web stays false.
    android_runtime: bool = False
    # Loopback API port inside the APK. Keep default in sync with
    # frontend/src/lib/androidLocalApi.json (Gradle copies that file into BuildConfig).
    android_api_port: int = 8787

    # Downloads (app-private on Android via DOWNLOAD_DIR from the bootstrap).
    download_dir: str = ""
    ffmpeg_path: str = ""
    android_native_lib_dir: str = ""
    min_download_free_bytes: int = 50 * 1024 * 1024

    # MX Player API
    api_base: str = "https://api.mxplayer.in/v1/web"
    cdn_image: str = "https://qqcdnpictest.mxplay.com"
    cdn_video: str = "https://llvod.mxplay.com"

    if _PYDANTIC_V2:
        model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
    else:
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"


settings = Settings()


def cors_allow_origins() -> list[str]:
    """Web keeps open CORS; Capacitor WebView is https://localhost → loopback API."""
    if settings.android_runtime:
        return ["https://localhost", "http://localhost"]
    return ["*"]


def cors_allow_credentials() -> bool:
    return not settings.android_runtime


# Reusable constants (kept flat for easy import)

DEFAULT_PARAMS: dict[str, str] = {
    "device-density": "3",
    "platform": "com.mxplay.desktop",
    "content-languages": "hi,en",
    "kids-mode-enabled": "false",
}

USER_AGENTS: list[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
]

BROWSER_HEADERS: dict[str, str] = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
    "Origin": "https://www.mxplayer.in",
    "Referer": "https://www.mxplayer.in/",
    "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "cross-site",
}
