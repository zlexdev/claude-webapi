"""Auth-flow enums: source app, credential method, locale."""

from enum import StrEnum


class SourceApp(StrEnum):
    CLAUDE = "claude"
    CONSOLE = "console"


class CredentialMethod(StrEnum):
    NONCE = "nonce"
    CODE = "code"


class Locale(StrEnum):
    EN_US = "en-US"
    EN_GB = "en-GB"
    RU_RU = "ru-RU"
    DE_DE = "de-DE"
    FR_FR = "fr-FR"
    ES_ES = "es-ES"
    PT_BR = "pt-BR"
    IT_IT = "it-IT"
    JA_JP = "ja-JP"
    KO_KR = "ko-KR"
    ZH_CN = "zh-CN"
