from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

# Путь к корневой папке проекта, где лежит файл .env
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE_PATH = BASE_DIR / ".env"



class DbSettings(BaseSettings):
    
    """Настройки БД с автоматическим поиском переменных с префиксом DB_"""
    
    HOST: str
    PORT: int
    NAME: str
    USER: str
    PASS: str
    
    @property
    def url_asyncpg(self) -> str:
        return f"postgresql+asyncpg://{self.USER}:{self.PASS}@{self.HOST}:{self.PORT}/{self.NAME}"


    model_config = SettingsConfigDict(env_prefix="DB_", extra="ignore")


class JwtSettings(BaseSettings):
    
    """Настройки JWT с автоматическим поиском переменных с префиксом JWT_"""
    
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    VERIFY_EMAIL_TOKEN_EXPIRE_HOURS: int
    RESET_PASSWORD_TOKEN_EXPIRE_MINUTES: int

    model_config = SettingsConfigDict(env_prefix="JWT_", extra="ignore")
    

class SMTPSettings(BaseSettings):
    
    """Данные для почты с автоматическим поиском переменных с префиксом SMTP_"""
    
    HOST: str
    PORT: int
    ADDRESS: str
    PASSWORD: str

    model_config = SettingsConfigDict(env_prefix="SMTP_", extra="ignore")
    

class RedisSettings(BaseSettings):
    
    """Настройки Redis с автоматическим поиском переменных с префиксом REDIS_"""
    
    HOST: str
    PORT: int
    DB_NUMBER: int
    
    @property
    def url(self) -> str:
        return f"redis://{self.HOST}:{self.PORT}/{self.DB_NUMBER}"


    model_config = SettingsConfigDict(env_prefix="REDIS_", extra="ignore")


class Settings(BaseSettings):
    """Главный класс, который собирает всё вместе"""
    
    # отдельно считываем переменные
    MODE: str # dev или test
    LOG_LEVEL: str # info/debug/error...
    
    db: DbSettings = DbSettings(_env_file=ENV_FILE_PATH)
    jwt: JwtSettings = JwtSettings(_env_file=ENV_FILE_PATH)
    smtp: SMTPSettings = SMTPSettings(_env_file=ENV_FILE_PATH)
    redis: RedisSettings = RedisSettings(_env_file=ENV_FILE_PATH)
    
    model_config = SettingsConfigDict(env_file=ENV_FILE_PATH, extra="ignore")
    

settings = Settings()

# пример обращения к настройкам
# settings.db.url_asyncpg
# settings.jwt.SECRET_KEY
# settings.MODE

