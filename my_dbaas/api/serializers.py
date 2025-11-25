from django.contrib.auth.models import User
from rest_framework import serializers

# 👇 Đảm bảo trong file api/models.py bạn đã đặt tên class là UserDatabase nhé
from .models import UserDatabase 


# 1. Serializer Đăng Ký
class Users(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "email", "password")

    def create(self, user_info):
        user = User.objects.create_user(
            username=user_info["username"],
            email=user_info["email"],
            password=user_info["password"],
        )
        return user


# 2. Serializer Đăng Nhập
class UserLogin(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        if not data.get("username") or not data.get("password"):
            raise serializers.ValidationError("Cần nhập đủ username và password")
        return data


# 3. Serializer Tạo Database (Provision)
class Provision(serializers.Serializer):
    # Thêm required=False để cho phép người dùng không điền tên (tự sinh)
    db_name = serializers.CharField(required=False, allow_blank=True, max_length=100)
    db_password = serializers.CharField(write_only=True, max_length=100)

    def validate(self, data):
        # Logic kiểm tra khoảng trắng của bạn rất tốt!
        if " " in data.get("db_password"):
            raise serializers.ValidationError(
                "Mật khẩu database không được chứa khoảng trắng."
            )

        # Kiểm tra tên DB nếu người dùng có nhập
        if data.get("db_name") and " " in data.get("db_name"):
            raise serializers.ValidationError(
                "Tên Database không được chứa khoảng trắng."
            )

        return data


# 4. Serializer Hiển thị danh sách (List)
class UserDatabaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDatabase
        # 👇 Mình đã thêm trường 'host' vào đây để Frontend hiển thị IP
        fields = ["id", "db_name", "db_user", "db_password", "host", "created_at"]