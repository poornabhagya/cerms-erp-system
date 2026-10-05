from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT Token Obtain serializer that adds user profile claims
    directly into the token payload and JSON response body for Mobile/API clients.
    """

    @classmethod
    def get_token(cls, user: User):
        token = super().get_token(user)

        # Custom claims inside token payload
        token['username'] = user.username
        token['email'] = user.email
        token['role'] = user.role
        token['employee_id'] = user.employee_id
        token['full_name'] = user.get_full_name()
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # Custom properties inside the JSON response
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'role': self.user.role,
            'role_display': self.user.get_role_display(),
            'employee_id': self.user.employee_id,
            'full_name': self.user.get_full_name(),
            'is_active': self.user.is_active,
        }
        return data


class UserSerializer(serializers.ModelSerializer):
    """Serializer for displaying authenticated user profile details."""
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'role',
            'role_display',
            'phone_number',
            'employee_id',
            'is_active',
            'date_joined',
        ]
        read_only_fields = ['id', 'role', 'role_display', 'date_joined']
