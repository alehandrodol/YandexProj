from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# берем параметры БД из переменных окружения //TODO поменять на переменные окружения
# DB_USER = environ.get("DB_USER", "user")
# DB_PASSWORD = environ.get("DB_PASSWORD", "password")
# DB_HOST = environ.get("DB_HOST", "localhost")
# DB_NAME = "async-blogs"
# SQLALCHEMY_DATABASE_URL = (
#     f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"
# )
# создаем объект database, который будет использоваться для выполнения запросов
# database = databases.Database(SQLALCHEMY_DATABASE_URL)


SQLALCHEMY_DATABASE_URL = "postgresql://postgres:tozafa30@localhost/YandexProject"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
