"""
File: test_database_operations.py

Overview:
This Python test file utilizes pytest to manage database states and HTTP clients for testing a web application built with FastAPI and SQLAlchemy. It includes detailed fixtures to mock the testing environment, ensuring each test is run in isolation with a consistent setup.

Fixtures:
- `async_client`: Manages an asynchronous HTTP client for testing interactions with the FastAPI application.
- `db_session`: Handles database transactions to ensure a clean database state for each test.
- User fixtures (`user`, `locked_user`, `verified_user`, etc.): Set up various user states to test different behaviors under diverse conditions.
- `token`: Generates an authentication token for testing secured endpoints.
- `initialize_database`: Prepares the database at the session start.
- `setup_database`: Sets up and tears down the database before and after each test.
"""

# Standard library imports
from builtins import range
from unittest.mock import patch
from uuid import uuid4

# Third-party imports
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, scoped_session
from faker import Faker

# Application-specific imports
from app.main import app
from app.database import Base, get_async_db, initialize_async_db
from app.models.user_model import User, UserRole
from app.dependencies import get_db, get_settings
from app.utils.security import hash_password

fake = Faker()

settings = get_settings()
TEST_DATABASE_URL = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
engine = create_async_engine(TEST_DATABASE_URL, echo=True)
AsyncTestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
AsyncSessionScoped = scoped_session(AsyncTestingSessionLocal)

@pytest.fixture(scope="function")
async def async_client(db_session):
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        app.dependency_overrides[get_async_db] = lambda: db_session
        try:
            yield client
        finally:
            app.dependency_overrides.clear()

@pytest.fixture(scope="function")
async def token():
    form_data = {
        "username": "admin",
        "password": "secret",
    }
    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        response = await ac.post("/token", data=form_data)
        assert response.status_code == 200  # Ensure the request was successful
        return response.json()["access_token"]

@pytest.fixture(scope="session", autouse=True)
def initialize_database():
    try:
        initialize_async_db(settings.database_url)
    except Exception as e:
        pytest.fail(f"Failed to initialize the database: {str(e)}")

@pytest.fixture(scope="function", autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture(scope="function")
async def db_session(setup_database):
    async with AsyncSessionScoped() as session:
        try:
            yield session
        finally:
            await session.close()

@pytest.fixture(scope="function")
async def locked_user(db_session):
    unique_email = fake.email()
    user_data = {
        "username": fake.user_name(),
        "email": unique_email,
        "hashed_password": hash_password("MySuperPassword$1234"),
        "role": UserRole.AUTHENTICATED,
        "email_verified": False,
        "is_locked": True,
        "failed_login_attempts": settings.max_login_attempts,
    }
    user = User(**user_data)
    db_session.add(user)
    await db_session.commit()
    return user

@pytest.fixture(scope="function")
async def user(db_session):
    unique_email = fake.email()
    user_data = {
        "username": fake.user_name(),
        "email": unique_email,
        "hashed_password": hash_password("MySuperPassword$1234"),
        "role": UserRole.AUTHENTICATED,
        "email_verified": False,
        "is_locked": False,
    }
    user = User(**user_data)
    db_session.add(user)
    await db_session.commit()
    return user

@pytest.fixture(scope="function")
async def verified_user(db_session):
    unique_email = fake.email()
    user_data = {
        "username": fake.user_name(),
        "email": unique_email,
        "hashed_password": hash_password("MySuperPassword$1234"),
        "role": UserRole.AUTHENTICATED,
        "email_verified": True,
        "is_locked": False,
    }
    user = User(**user_data)
    db_session.add(user)
    await db_session.commit()
    return user

@pytest.fixture(scope="function")
async def users_with_same_role_50_users(db_session):
    users = []
    for _ in range(50):
        unique_email = fake.email()
        user_data = {
            "username": fake.user_name(),
            "email": unique_email,
            "hashed_password": fake.password(),
            "role": UserRole.AUTHENTICATED,
            "email_verified": False,
            "is_locked": False,
        }
        user = User(**user_data)
        db_session.add(user)
        users.append(user)
    await db_session.commit()
    return users

@pytest.fixture
async def admin_user(db_session: AsyncSession):
    user = User(
        username="admin_user",
        email="admin@example.com",
        hashed_password="securepassword",
        role=UserRole.ADMIN,
        is_locked=False,
    )
    db_session.add(user)
    await db_session.commit()
    return user

@pytest.fixture
async def manager_user(db_session: AsyncSession):
    user = User(
        username="manager_user",
        email="manager_user@example.com",
        hashed_password="securepassword",
        role=UserRole.MANAGER,
        is_locked=False,
    )
    db_session.add(user)
    await db_session.commit()
    return user
