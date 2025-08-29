#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Migrated admin fields tests using optimized fixtures for better performance.

This file replaces the original admin fields test with:
1. Pytest fixtures instead of create_ctfd/destroy_ctfd per test
2. Dynamic ID handling instead of hardcoded IDs
3. Better test isolation and cleanup
4. Parametrized tests for different field configurations
"""

from CTFd.models import Users
from tests.helpers import (
    gen_field,
    gen_team,
    login_as_user,
    register_user,
)


class TestAdminFields:
    """Test admin field management functionality"""
    
    def test_admin_view_fields(self, clean_db):
        """Test that admin can view all user fields regardless of visibility"""
        register_user(clean_db)
        user = Users.query.filter_by(email="user@examplectf.com").first()

        # Create fields with different visibility settings
        gen_field(
            clean_db.db, name="CustomField1", required=True, public=True, editable=True
        )
        gen_field(
            clean_db.db, name="CustomField2", required=False, public=True, editable=True
        )
        gen_field(
            clean_db.db, name="CustomField3", required=False, public=False, editable=True
        )
        gen_field(
            clean_db.db, name="CustomField4", required=False, public=False, editable=False
        )

        with login_as_user(clean_db, name="admin") as admin:
            # Admins should see all user fields regardless of public or editable
            r = admin.get(f"/admin/users/{user.id}")
            resp = r.get_data(as_text=True)
            assert "CustomField1" in resp
            assert "CustomField2" in resp
            assert "CustomField3" in resp
            assert "CustomField4" in resp

    def test_admin_view_team_fields(self, clean_db_with_data_team_mode):
        """Test that admin can view all team fields regardless of visibility"""
        register_user(clean_db_with_data_team_mode)
        team = gen_team(clean_db_with_data_team_mode.db)
        user = Users.query.filter_by(email="user@examplectf.com").first()
        user.team_id = team.id
        clean_db_with_data_team_mode.db.session.commit()

        # Create team fields with different visibility settings
        gen_field(
            clean_db_with_data_team_mode.db,
            name="CustomField1",
            type="team",
            required=True,
            public=True,
            editable=True,
        )
        gen_field(
            clean_db_with_data_team_mode.db,
            name="CustomField2",
            type="team",
            required=False,
            public=True,
            editable=True,
        )
        gen_field(
            clean_db_with_data_team_mode.db,
            name="CustomField3",
            type="team",
            required=False,
            public=False,
            editable=True,
        )
        gen_field(
            clean_db_with_data_team_mode.db,
            name="CustomField4",
            type="team",
            required=False,
            public=False,
            editable=False,
        )

        with login_as_user(clean_db_with_data_team_mode, name="admin") as admin:
            # Admins should see all team fields regardless of public or editable
            r = admin.get(f"/admin/teams/{team.id}")
            resp = r.get_data(as_text=True)
            assert "CustomField1" in resp
            assert "CustomField2" in resp
            assert "CustomField3" in resp
            assert "CustomField4" in resp
