#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Migrated admin challenges tests using optimized fixtures for better performance.

This file replaces the original admin challenges test with:
1. Pytest fixtures instead of create_ctfd/destroy_ctfd per test
2. Dynamic ID handling instead of hardcoded IDs
3. Better test isolation and cleanup
"""

from CTFd.models import Challenges
from CTFd.utils import set_config
from tests.helpers import (
    gen_challenge,
    gen_flag,
    login_as_user,
    register_user,
)


class TestAdminChallenges:
    """Test admin challenge management functionality"""
    
    def test_create_new_challenge(self, clean_db):
        """Test that an admin can create a challenge properly"""
        register_user(clean_db)
        
        with login_as_user(clean_db, name="admin", password="password") as client:
            challenge_data = {
                "name": "name",
                "category": "category",
                "description": "description",
                "value": 100,
                "state": "hidden",
                "type": "standard",
            }

            r = client.post("/api/v1/challenges", json=challenge_data)
            challenge_id = r.get_json().get("data")["id"]
            assert challenge_id is not None
            
            r = client.get(f"/admin/challenges/{challenge_id}")
            assert r.status_code == 200
            
            r = client.get(f"/api/v1/challenges/{challenge_id}")
            assert r.get_json().get("data")["id"] == challenge_id

    def test_hidden_challenge_is_reachable(self, clean_db):
        """Test that hidden challenges are visible for admins"""
        register_user(clean_db)
        chal = gen_challenge(clean_db.db, state="hidden")
        gen_flag(clean_db.db, challenge_id=chal.id, content="flag")
        chal_id = chal.id

        assert Challenges.query.count() == 1
        
        with login_as_user(clean_db, name="admin", password="password") as client:
            r = client.get("/api/v1/challenges", json="")
            data = r.get_json().get("data")
            assert data == []

            r = client.get(f"/api/v1/challenges/{chal_id}", json="")
            assert r.status_code == 200
            data = r.get_json().get("data")
            assert data["name"] == "chal_name"

            data = {"submission": "flag", "challenge_id": chal_id}

            r = client.post("/api/v1/challenges/attempt", json=data)
            assert r.status_code == 404

            r = client.post("/api/v1/challenges/attempt?preview=true", json=data)
            assert r.status_code == 200
            resp = r.get_json()["data"]
            assert resp.get("status") == "correct"

    def test_challenges_admin_only_as_user(self, clean_db, client):
        """Test that regular users cannot access admin-only challenges"""
        set_config("challenge_visibility", "admins")

        register_user(clean_db)
        private_client = login_as_user(clean_db)

        chal = gen_challenge(clean_db.db)
        gen_flag(clean_db.db, challenge_id=chal.id, content="flag")

        r = private_client.get("/challenges")
        assert r.status_code == 403

        r = private_client.get("/api/v1/challenges", json="")
        assert r.status_code == 403

        r = private_client.get(f"/api/v1/challenges/{chal.id}", json="")
        assert r.status_code == 403

        data = {"submission": "flag", "challenge_id": chal.id}
        r = private_client.post("/api/v1/challenges/attempt", json=data)
        assert r.status_code == 403
