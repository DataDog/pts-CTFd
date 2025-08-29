#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Migrated user hints tests using optimized fixtures for better performance.

This file replaces the original hints tests with:
1. Pytest fixtures instead of create_ctfd/destroy_ctfd per test
2. Dynamic ID handling instead of hardcoded IDs
3. Better test isolation and cleanup
4. Parametrized tests where appropriate
"""

from freezegun import freeze_time

from CTFd.models import Unlocks, Users
from CTFd.utils import set_config, text_type
from tests.helpers import (
    gen_award,
    gen_challenge,
    gen_flag,
    gen_hint,
    login_as_user,
    register_user,
)


class TestUserHints:
    """Test user hint functionality"""
    
    def test_user_cannot_unlock_hint(self, clean_db, client):
        """Test that a user can't unlock a hint if they don't have enough points"""
        register_user(clean_db, name="user1", email="user1@examplectf.com")

        chal = gen_challenge(clean_db.db, value=100)
        gen_flag(clean_db.db, challenge_id=chal.id, content="flag")
        hint = gen_hint(clean_db.db, chal.id, cost=10)
        hint_id = hint.id  # Store the ID instead of the object

        private_client = login_as_user(clean_db, name="user1", password="password")

        r = private_client.get(f"/api/v1/hints/{hint_id}")
        resp = r.get_json()
        assert resp["data"].get("content") is None
        assert resp["data"].get("cost") == 10


    def test_user_can_unlock_hint(self, clean_db, client):
        """Test that a user can unlock a hint if they have enough points"""
        register_user(clean_db, name="user1", email="user1@examplectf.com")
        user = Users.query.filter_by(name="user1").first()
        user_id = user.id

        chal = gen_challenge(clean_db.db, value=100)
        gen_flag(clean_db.db, challenge_id=chal.id, content="flag")
        hint = gen_hint(clean_db.db, chal.id, cost=10)
        hint_id = hint.id

        gen_award(clean_db.db, user_id=user_id, value=15)

        private_client = login_as_user(clean_db, name="user1", password="password")

        user = Users.query.filter_by(id=user_id).first()
        assert user.score == 15

        # Check hint is locked initially
        r = private_client.get(f"/api/v1/hints/{hint_id}")
        resp = r.get_json()
        assert resp["data"].get("content") is None

        # Unlock the hint
        params = {"target": hint_id, "type": "hints"}
        r = private_client.post("/api/v1/unlocks", json=params)
        resp = r.get_json()
        assert resp["success"] is True

        # Check hint is now unlocked
        r = private_client.get(f"/api/v1/hints/{hint_id}")
        resp = r.get_json()
        assert resp["data"].get("content") == "This is a hint"

        # Check score was deducted
        user = Users.query.filter_by(id=user_id).first()
        assert user.score == 5


    def test_unlocking_hints_with_no_cost(self, clean_db, client):
        """Test that hints with no cost can be unlocked"""
        register_user(clean_db)
        chal = gen_challenge(clean_db.db)
        hint = gen_hint(clean_db.db, chal.id)
        hint_id = hint.id
        
        private_client = login_as_user(clean_db)
        r = private_client.get(f"/api/v1/hints/{hint_id}")
        resp = r.get_json()["data"]
        assert resp.get("content") == "This is a hint"


    def test_unlocking_hints_with_cost_during_ctf_with_points(self, clean_db, client):
        """Test that hints with a cost are unlocked if you have the points"""
        register_user(clean_db)
        user = Users.query.filter_by(email="user@examplectf.com").first()
        user_id = user.id
        
        chal = gen_challenge(clean_db.db)
        hint = gen_hint(clean_db.db, chal.id, cost=10)
        hint_id = hint.id
        gen_award(clean_db.db, user_id=user_id)

        private_client = login_as_user(clean_db)
        r = private_client.get(f"/api/v1/hints/{hint_id}")
        assert r.get_json()["data"].get("content") is None

        private_client.post("/api/v1/unlocks", json={"target": hint_id, "type": "hints"})

        r = private_client.get(f"/api/v1/hints/{hint_id}")
        assert r.get_json()["data"].get("content") == "This is a hint"

        user = Users.query.filter_by(id=user_id).first()
        assert user.score == 90


    def test_unlocking_hints_with_cost_during_ctf_without_points(self, clean_db, client):
        """Test that hints with a cost are not unlocked if you don't have the points"""
        register_user(clean_db)
        user = Users.query.filter_by(email="user@examplectf.com").first()
        user_id = user.id
        
        chal = gen_challenge(clean_db.db)
        hint = gen_hint(clean_db.db, chal.id, cost=10)
        hint_id = hint.id

        private_client = login_as_user(clean_db)

        r = private_client.get(f"/api/v1/hints/{hint_id}")
        assert r.get_json()["data"].get("content") is None

        r = private_client.post("/api/v1/unlocks", json={"target": hint_id, "type": "hints"})
        assert (
            r.get_json()["errors"]["score"]
            == "You do not have enough points to unlock this hint"
        )

        r = private_client.get(f"/api/v1/hints/{hint_id}")
        assert r.get_json()["data"].get("content") is None

        user = Users.query.filter_by(id=user_id).first()
        assert user.score == 0


    def test_unlocking_hints_with_cost_before_ctf(self, clean_db, client):
        """Test that hints are not unlocked if the CTF hasn't begun"""
        register_user(clean_db)
        user = Users.query.filter_by(email="user@examplectf.com").first()
        user_id = user.id
        
        chal = gen_challenge(clean_db.db)
        hint = gen_hint(clean_db.db, chal.id)
        hint_id = hint.id
        gen_award(clean_db.db, user_id=user_id)

        set_config(
            "start", "1507089600"
        )  # Wednesday, October 4, 2017 12:00:00 AM GMT-04:00 DST
        set_config(
            "end", "1507262400"
        )  # Friday, October 6, 2017 12:00:00 AM GMT-04:00 DST

        with freeze_time("2017-10-1"):
            private_client = login_as_user(clean_db)

            r = private_client.get(f"/api/v1/hints/{hint_id}")
            assert r.status_code == 403
            assert r.get_json().get("data") is None

            r = private_client.post("/api/v1/unlocks", json={"target": hint_id, "type": "hints"})
            assert r.status_code == 403
            assert r.get_json().get("data") is None

            r = private_client.get(f"/api/v1/hints/{hint_id}")
            assert r.get_json().get("data") is None
            assert r.status_code == 403

            user = Users.query.filter_by(id=user_id).first()

            assert user.score == 100
            assert Unlocks.query.count() == 0


    def test_unlocking_hints_with_cost_during_ended_ctf(self, clean_db, client):
        """Test that hints with a cost are not unlocked if the CTF has ended"""
        register_user(clean_db)
        user = Users.query.filter_by(email="user@examplectf.com").first()
        user_id = user.id
        
        chal = gen_challenge(clean_db.db)
        hint = gen_hint(clean_db.db, chal.id, cost=10)
        hint_id = hint.id
        gen_award(clean_db.db, user_id=user_id)

        set_config(
            "start", "1507089600"
        )  # Wednesday, October 4, 2017 12:00:00 AM GMT-04:00 DST
        set_config(
            "end", "1507262400"
        )  # Friday, October 6, 2017 12:00:00 AM GMT-04:00 DST

        with freeze_time("2017-11-4"):
            private_client = login_as_user(clean_db)

            r = private_client.get(f"/api/v1/hints/{hint_id}")
            assert r.get_json().get("data") is None
            assert r.status_code == 403

            r = private_client.post("/api/v1/unlocks", json={"target": hint_id, "type": "hints"})
            assert r.status_code == 403
            assert r.get_json()

            r = private_client.get(f"/api/v1/hints/{hint_id}")
            assert r.status_code == 403

            user = Users.query.filter_by(id=user_id).first()
            assert user.score == 100
            assert Unlocks.query.count() == 0


    def test_unlocking_hints_with_cost_during_frozen_ctf(self, clean_db, client):
        """Test that hints with a cost are unlocked if the CTF is frozen."""
        set_config(
            "freeze", "1507262400"
        )  # Friday, October 6, 2017 12:00:00 AM GMT-04:00 DST
        
        user_id = None
        hint_id = None
        
        with freeze_time("2017-10-4"):
            register_user(clean_db)
            user = Users.query.filter_by(email="user@examplectf.com").first()
            user_id = user.id
            
            chal = gen_challenge(clean_db.db)
            hint = gen_hint(clean_db.db, chal.id, cost=10)
            hint_id = hint.id
            gen_award(clean_db.db, user_id=user_id)

        with freeze_time("2017-10-8"):
            private_client = login_as_user(clean_db)

            private_client.get(f"/api/v1/hints/{hint_id}")

            private_client.post("/api/v1/unlocks", json={"target": hint_id, "type": "hints"})

            r = private_client.get(f"/api/v1/hints/{hint_id}")

            resp = r.get_json()["data"]
            assert resp.get("content") == "This is a hint"

            user = Users.query.filter_by(id=user_id).first()
            assert user.score == 100


    def test_unlocking_hint_for_unicode_challenge(self, clean_db, client):
        """Test that hints for challenges with unicode names can be unlocked"""
        register_user(clean_db)
        chal = gen_challenge(clean_db.db, name=text_type("🐺"))
        hint = gen_hint(clean_db.db, chal.id)
        hint_id = hint.id

        private_client = login_as_user(clean_db)

        r = private_client.get(f"/api/v1/hints/{hint_id}")
        assert r.status_code == 200
        resp = r.get_json()["data"]
        assert resp.get("content") == "This is a hint"
