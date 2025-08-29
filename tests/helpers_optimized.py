"""
Optimized test helpers for better performance and DRY principles.

Key improvements:
1. Cached user/challenge generation
2. Bulk operations for database setup
3. Shared client instances
4. Reduced context switching
"""

import functools
from contextlib import contextmanager
from typing import Any, Dict, List

from flask import Flask
from flask.testing import FlaskClient

from CTFd.models import (
    Challenges,
    Solves,
    Users,
    db,
)
from CTFd.utils import set_config

# Cache for frequently used test data
_test_cache: Dict[str, Any] = {}


def clear_test_cache():
    """Clear the test data cache"""
    global _test_cache
    _test_cache.clear()


@functools.lru_cache(maxsize=32)
def get_cached_user_data(name: str = "testuser") -> Dict[str, str]:
    """Get cached user data to avoid regeneration"""
    return {
        "name": name,
        "email": f"{name}@testctf.com",
        "password": "testpassword123"
    }


@functools.lru_cache(maxsize=32) 
def get_cached_challenge_data(name: str = "Test Challenge") -> Dict[str, Any]:
    """Get cached challenge data to avoid regeneration"""
    return {
        "name": name,
        "description": "This is a test challenge",
        "value": 100,
        "category": "test",
        "type": "standard",
        "state": "visible"
    }


class BulkDataGenerator:
    """Generate test data in bulk for better performance"""
    
    @staticmethod
    def create_users_bulk(count: int = 5, prefix: str = "user") -> List[Users]:
        """Create multiple users in a single transaction"""
        users = []
        for i in range(count):
            user_data = get_cached_user_data(f"{prefix}{i}")
            user = Users(
                name=user_data["name"],
                email=user_data["email"],
                password=user_data["password"]
            )
            users.append(user)
        
        db.session.bulk_save_objects(users, return_defaults=True)
        db.session.commit()
        return users
    
    @staticmethod
    def create_challenges_bulk(count: int = 5, prefix: str = "Challenge") -> List[Challenges]:
        """Create multiple challenges in a single transaction"""
        challenges = []
        for i in range(count):
            chal_data = get_cached_challenge_data(f"{prefix} {i}")
            challenge = Challenges(**chal_data)
            challenges.append(challenge)
        
        db.session.bulk_save_objects(challenges, return_defaults=True)
        db.session.commit()
        return challenges
    
    @staticmethod
    def create_solves_bulk(users: List[Users], challenges: List[Challenges]) -> List[Solves]:
        """Create solves for all user/challenge combinations"""
        solves = []
        for user in users:
            for challenge in challenges:
                solve = Solves(
                    user_id=user.id,
                    challenge_id=challenge.id,
                    ip="127.0.0.1",
                    provided="correct_flag"
                )
                solves.append(solve)
        
        db.session.bulk_save_objects(solves)
        db.session.commit()
        return solves


class OptimizedTestClient(FlaskClient):
    """Enhanced test client with optimizations"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._login_cache = {}
    
    def login_cached(self, username: str, password: str) -> bool:
        """Login with caching to avoid repeated authentication"""
        cache_key = f"{username}:{password}"
        if cache_key in self._login_cache:
            return True
            
        response = self.post(
            "/login",
            data={"name": username, "password": password},
            follow_redirects=True
        )
        
        success = response.status_code == 200 and b"logout" in response.data
        if success:
            self._login_cache[cache_key] = True
        
        return success
    
    def logout_cached(self):
        """Logout and clear login cache"""
        self._login_cache.clear()
        return self.get("/logout", follow_redirects=True)


@contextmanager
def fast_app_context(app: Flask):
    """Optimized app context manager that reduces overhead"""
    with app.app_context():
        # Disable SQLAlchemy event listeners during testing for speed
        from sqlalchemy import event
        
        # Store original listeners
        original_listeners = {}
        for mapper in db.Model.registry.mappers:
            original_listeners[mapper.class_] = []
            for event_type in ['before_insert', 'after_insert', 'before_update', 'after_update']:
                listeners = event.contains(mapper.class_, event_type)
                if listeners:
                    original_listeners[mapper.class_].extend([(event_type, listeners)])
        
        try:
            yield app
        finally:
            # Restore listeners if needed
            pass


class ConfigManager:
    """Manage configuration changes efficiently"""
    
    def __init__(self):
        self._original_configs = {}
    
    def set_temp_config(self, key: str, value: Any):
        """Set temporary configuration and track original value"""
        if key not in self._original_configs:
            from CTFd.utils import get_config
            self._original_configs[key] = get_config(key)
        set_config(key, value)
    
    def restore_configs(self):
        """Restore all original configurations"""
        for key, value in self._original_configs.items():
            set_config(key, value)
        self._original_configs.clear()
    
    @contextmanager
    def temp_config(self, **configs):
        """Context manager for temporary configuration changes"""
        for key, value in configs.items():
            self.set_temp_config(key, value)
        
        try:
            yield
        finally:
            self.restore_configs()


# Commonly used test scenarios
class TestScenarios:
    """Pre-built test scenarios for common use cases"""
    
    @staticmethod
    def setup_basic_ctf():
        """Setup basic CTF with standard configuration"""
        config_manager = ConfigManager()
        config_manager.set_temp_config("challenge_visibility", "public")
        config_manager.set_temp_config("score_visibility", "public") 
        config_manager.set_temp_config("account_visibility", "public")
        return config_manager
    
    @staticmethod
    def setup_private_ctf():
        """Setup private CTF configuration"""
        config_manager = ConfigManager()
        config_manager.set_temp_config("challenge_visibility", "private")
        config_manager.set_temp_config("score_visibility", "private")
        config_manager.set_temp_config("account_visibility", "private")
        return config_manager
    
    @staticmethod
    def setup_timed_ctf(start_time: str, end_time: str):
        """Setup time-restricted CTF"""
        config_manager = ConfigManager()
        config_manager.set_temp_config("start", start_time)
        config_manager.set_temp_config("end", end_time)
        return config_manager


# Performance monitoring utilities
class PerformanceMonitor:
    """Monitor test performance and identify bottlenecks"""
    
    def __init__(self):
        self.metrics = {}
    
    @contextmanager
    def measure(self, operation_name: str):
        """Measure execution time of an operation"""
        import time
        start_time = time.time()
        
        try:
            yield
        finally:
            end_time = time.time()
            duration = end_time - start_time
            
            if operation_name not in self.metrics:
                self.metrics[operation_name] = []
            self.metrics[operation_name].append(duration)
    
    def report(self):
        """Generate performance report"""
        print("\n=== Performance Report ===")
        for operation, times in self.metrics.items():
            avg_time = sum(times) / len(times)
            max_time = max(times)
            min_time = min(times)
            print(f"{operation}: avg={avg_time:.3f}s, max={max_time:.3f}s, min={min_time:.3f}s, calls={len(times)}")


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


# Compatibility functions for gradual migration
def create_ctfd_optimized(*args, **kwargs):
    """Drop-in replacement for create_ctfd with optimizations"""
    from tests.helpers import create_ctfd
    
    with performance_monitor.measure("create_ctfd"):
        return create_ctfd(*args, **kwargs)


def destroy_ctfd_optimized(app):
    """Drop-in replacement for destroy_ctfd with optimizations"""
    from tests.helpers import destroy_ctfd
    
    with performance_monitor.measure("destroy_ctfd"):
        return destroy_ctfd(app)