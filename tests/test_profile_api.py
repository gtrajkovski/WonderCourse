"""Tests for profile management and password change API endpoints."""

import pytest


class TestGetProfile:
    """Tests for GET /api/auth/profile endpoint."""

    def test_get_profile_authenticated(self, authenticated_client):
        """Authenticated user can view their profile."""
        response = authenticated_client.get('/api/auth/profile')

        assert response.status_code == 200
        data = response.get_json()
        assert data['email'] == 'test@example.com'
        assert data['name'] == 'Test User'
        assert 'id' in data
        assert 'password_hash' not in data

    def test_get_profile_unauthenticated(self, auth_app):
        """Unauthenticated user cannot view profile."""
        client = auth_app.test_client()
        response = client.get('/api/auth/profile')

        assert response.status_code == 401


class TestUpdateProfile:
    """Tests for PUT /api/auth/profile endpoint."""

    def test_update_name(self, authenticated_client):
        """User can update their name."""
        response = authenticated_client.put('/api/auth/profile', json={
            'name': 'Updated Name'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['name'] == 'Updated Name'
        assert data['email'] == 'test@example.com'

    def test_update_email(self, authenticated_client):
        """User can update their email."""
        response = authenticated_client.put('/api/auth/profile', json={
            'email': 'newemail@example.com'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['email'] == 'newemail@example.com'
        assert data['name'] == 'Test User'

    def test_update_email_duplicate(self, authenticated_client):
        """User cannot update to an email already in use."""
        # Register another user
        authenticated_client.post('/api/auth/register', json={
            'email': 'other@example.com',
            'password': 'password123',
            'name': 'Other User'
        })

        # Try to update to that email
        response = authenticated_client.put('/api/auth/profile', json={
            'email': 'other@example.com'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'already in use' in data['error'].lower()

    def test_update_profile_both_fields(self, authenticated_client):
        """User can update both name and email at once."""
        response = authenticated_client.put('/api/auth/profile', json={
            'name': 'New Name',
            'email': 'newboth@example.com'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['name'] == 'New Name'
        assert data['email'] == 'newboth@example.com'

    def test_update_profile_partial_name_only(self, authenticated_client):
        """User can update just name leaving email unchanged."""
        original = authenticated_client.get('/api/auth/profile').get_json()

        response = authenticated_client.put('/api/auth/profile', json={
            'name': 'Name Only Update'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['name'] == 'Name Only Update'
        assert data['email'] == original['email']

    def test_update_profile_unauthenticated(self, auth_app):
        """Unauthenticated user cannot update profile."""
        client = auth_app.test_client()
        response = client.put('/api/auth/profile', json={
            'name': 'Hacker'
        })

        assert response.status_code == 401

    def test_update_profile_empty_body(self, authenticated_client):
        """Empty update keeps profile unchanged."""
        original = authenticated_client.get('/api/auth/profile').get_json()

        response = authenticated_client.put('/api/auth/profile', json={})

        assert response.status_code == 200
        data = response.get_json()
        assert data['name'] == original['name']
        assert data['email'] == original['email']

    def test_update_profile_no_json(self, authenticated_client):
        """Request without JSON body returns 415 (Unsupported Media Type)."""
        response = authenticated_client.put('/api/auth/profile')

        # Flask returns 415 when Content-Type is not application/json
        assert response.status_code == 415


class TestChangePassword:
    """Tests for POST /api/auth/password endpoint."""

    def test_change_password_success(self, authenticated_client):
        """User can change password with correct current password."""
        response = authenticated_client.post('/api/auth/password', json={
            'current_password': 'testpassword123',
            'new_password': 'newpassword456'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert 'successfully' in data['message'].lower()

    def test_change_password_wrong_current(self, authenticated_client):
        """Wrong current password returns 400."""
        response = authenticated_client.post('/api/auth/password', json={
            'current_password': 'wrongpassword',
            'new_password': 'newpassword456'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'incorrect' in data['error'].lower()

    def test_change_password_too_short(self, authenticated_client):
        """Password shorter than 8 characters returns 400."""
        response = authenticated_client.post('/api/auth/password', json={
            'current_password': 'testpassword123',
            'new_password': 'short'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert '8 characters' in data['error']

    def test_change_password_missing_current(self, authenticated_client):
        """Missing current password returns 400."""
        response = authenticated_client.post('/api/auth/password', json={
            'new_password': 'newpassword456'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'required' in data['error'].lower()

    def test_change_password_missing_new(self, authenticated_client):
        """Missing new password returns 400."""
        response = authenticated_client.post('/api/auth/password', json={
            'current_password': 'testpassword123'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'required' in data['error'].lower()

    def test_change_password_missing_both(self, authenticated_client):
        """Missing both passwords returns 400."""
        response = authenticated_client.post('/api/auth/password', json={})

        assert response.status_code == 400

    def test_change_password_unauthenticated(self, auth_app):
        """Unauthenticated user cannot change password."""
        client = auth_app.test_client()
        response = client.post('/api/auth/password', json={
            'current_password': 'anypassword',
            'new_password': 'newpassword456'
        })

        assert response.status_code == 401

    def test_change_password_no_json(self, authenticated_client):
        """Request without JSON body returns 415 (Unsupported Media Type)."""
        response = authenticated_client.post('/api/auth/password')

        # Flask returns 415 when Content-Type is not application/json
        assert response.status_code == 415


class TestPasswordVerification:
    """Tests verifying password changes work correctly for login."""

    def test_old_password_invalid_after_change(self, auth_app):
        """Old password no longer works after password change."""
        client = auth_app.test_client()

        # Register and login
        client.post('/api/auth/register', json={
            'email': 'pwtest@example.com',
            'password': 'oldpassword123',
            'name': 'PW Test'
        })
        client.post('/api/auth/login', json={
            'email': 'pwtest@example.com',
            'password': 'oldpassword123'
        })

        # Change password
        response = client.post('/api/auth/password', json={
            'current_password': 'oldpassword123',
            'new_password': 'newpassword456'
        })
        assert response.status_code == 200

        # Logout
        client.post('/api/auth/logout')

        # Try to login with old password
        response = client.post('/api/auth/login', json={
            'email': 'pwtest@example.com',
            'password': 'oldpassword123'
        })
        assert response.status_code == 401

    def test_can_login_with_new_password(self, auth_app):
        """New password works for login after change."""
        client = auth_app.test_client()

        # Register and login
        client.post('/api/auth/register', json={
            'email': 'pwtest2@example.com',
            'password': 'oldpassword123',
            'name': 'PW Test 2'
        })
        client.post('/api/auth/login', json={
            'email': 'pwtest2@example.com',
            'password': 'oldpassword123'
        })

        # Change password
        response = client.post('/api/auth/password', json={
            'current_password': 'oldpassword123',
            'new_password': 'newpassword456'
        })
        assert response.status_code == 200

        # Logout
        client.post('/api/auth/logout')

        # Login with new password
        response = client.post('/api/auth/login', json={
            'email': 'pwtest2@example.com',
            'password': 'newpassword456'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['user']['email'] == 'pwtest2@example.com'
