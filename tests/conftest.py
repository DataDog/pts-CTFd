import uuid

import pytest
from sqlalchemy.engine.url import make_url
from sqlalchemy_utils import database_exists, drop_database

from CTFd import create_app
from CTFd.cache import cache
from CTFd.config import TestingConfig
from CTFd.models import db
from tests.helpers import CTFdTestClient, setup_ctfd


class OptimizedTestingConfig(TestingConfig):
    """Optimized testing configuration for better performance"""
    # Use faster cache backend
    CACHE_TYPE = "simple"
    # Disable unnecessary features during testing
    CSRF_ENABLED = False
    WTF_CSRF_ENABLED = False
    # Use faster session interface
    SESSION_TYPE = "filesystem"


@pytest.fixture(scope="session")
def app():
    """Session-scoped app fixture to reduce database creation overhead"""
    config = OptimizedTestingConfig
    
    # Create unique database for this session
    url = make_url(config.SQLALCHEMY_DATABASE_URI)
    if url.database:
        url = url.set(database=str(uuid.uuid4()))
    config.SQLALCHEMY_DATABASE_URI = str(url)
    
    app = create_app(config)
    app.test_client_class = CTFdTestClient
    
    with app.app_context():
        # Create tables once for the session
        db.create_all()
        
        # Setup basic CTF configuration
        app = setup_ctfd(
            app,
            ctf_name="Test CTF",
            ctf_description="Test Description",
            name="admin",
            email="admin@ctfd.io",
            password="password",
            user_mode="users",
        )
    
    yield app
    
    # Cleanup
    with app.app_context():
        if database_exists(config.SQLALCHEMY_DATABASE_URI):
            drop_database(config.SQLALCHEMY_DATABASE_URI)


@pytest.fixture(scope="function")
def app_ctx(app):
    """Function-scoped app context fixture"""
    with app.app_context():
        yield app


@pytest.fixture(scope="function") 
def client(app_ctx):
    """Function-scoped test client fixture"""
    with app_ctx.test_client() as client:
        yield client


@pytest.fixture(scope="function")
def clean_db(app_ctx):
    """Function-scoped fixture that provides a clean database state"""
    # Clear cache before each test
    cache.clear()
    
    # Truncate all tables but keep schema
    with app_ctx.app_context():
        # Disable foreign key checks for SQLite
        if 'sqlite' in str(db.engine.url):
            db.session.execute(db.text('PRAGMA foreign_keys = OFF'))
        
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
            # Reset auto-increment counter for SQLite
            if 'sqlite' in str(db.engine.url):
                # Check if sqlite_sequence table exists first
                result = db.session.execute(db.text("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'"))
                if result.fetchone():
                    db.session.execute(db.text(f'DELETE FROM sqlite_sequence WHERE name="{table.name}"'))
        
        # Re-enable foreign key checks
        if 'sqlite' in str(db.engine.url):
            db.session.execute(db.text('PRAGMA foreign_keys = ON'))
            
        db.session.commit()
        
        # Re-setup basic CTF configuration
        app_ctx = setup_ctfd(
            app_ctx,
            ctf_name="Test CTF", 
            ctf_description="Test Description",
            name="admin",
            email="admin@ctfd.io",
            password="password", 
            user_mode="users",
        )
    
    yield app_ctx
    
    # No cleanup needed - next test will clean


@pytest.fixture(scope="function")
def clean_db_with_data(clean_db):
    """Clean database with initial configuration for admin reset tests"""
    # This is essentially clean_db but with a descriptive name for admin tests
    yield clean_db


@pytest.fixture(scope="function") 
def clean_db_with_data_team_mode(app):
    """Clean database configured in team mode for admin reset tests"""
    # Clear cache
    cache.clear()
    
    # Truncate all tables but keep schema
    with app.app_context():
        # Disable foreign key checks for SQLite
        if 'sqlite' in str(db.engine.url):
            db.session.execute(db.text('PRAGMA foreign_keys = OFF'))
        
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
            # Reset auto-increment counter for SQLite
            if 'sqlite' in str(db.engine.url):
                # Check if sqlite_sequence table exists first
                result = db.session.execute(db.text("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'"))
                if result.fetchone():
                    db.session.execute(db.text(f'DELETE FROM sqlite_sequence WHERE name="{table.name}"'))
        
        # Re-enable foreign key checks
        if 'sqlite' in str(db.engine.url):
            db.session.execute(db.text('PRAGMA foreign_keys = ON'))
            
        db.session.commit()
        
        # Re-setup basic CTF configuration in TEAM mode
        app = setup_ctfd(
            app,
            ctf_name="Test CTF", 
            ctf_description="Test Description",
            name="admin",
            email="admin@ctfd.io",
            password="password", 
            user_mode="teams",  # Team mode for this fixture
        )
    
    yield app


@pytest.fixture(scope="function")
def quick_app():
    """Lightweight app fixture for tests that need isolation"""
    config = OptimizedTestingConfig
    config.SQLALCHEMY_DATABASE_URI = "sqlite://"  # In-memory
    
    app = create_app(config)
    app.test_client_class = CTFdTestClient
    
    yield app
    
    # Memory cleanup happens automatically with in-memory DB


# Pytest configuration for better performance
def pytest_configure(config):
    """Configure pytest for optimal performance"""
    # Add custom markers
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


def pytest_collection_modifyitems(config, items):
    """Modify test collection for better organization"""
    for item in items:
        # Auto-mark slow tests
        if "create_ctfd" in str(item.function):
            item.add_marker(pytest.mark.slow)
        
        # Auto-mark integration tests
        if any(path in str(item.fspath) for path in ["api", "admin", "themes"]):
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)


# Performance monitoring
@pytest.fixture(autouse=True, scope="session")
def performance_monitor():
    """Monitor test performance"""
    import time
    start_time = time.time()
    
    yield
    
    end_time = time.time()
    total_time = end_time - start_time
    print(f"\n\nTotal test suite execution time: {total_time:.2f} seconds")