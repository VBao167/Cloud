from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny # Thêm AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

# 👇 QUAN TRỌNG: Import thư viện Token
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication

from .models import UserDatabase
from .serializers import Provision, UserDatabaseSerializer, UserLogin, Users
from .utils import create_database_and_user, delete_database_from_mysql


# API để tạo người dùng mới (Đăng ký)
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = Users
    # Cho phép bất kỳ ai cũng được đăng ký
    permission_classes = [AllowAny]


# View Đăng nhập (Trả về Token)
class LoginView(APIView):
    # Không yêu cầu đăng nhập/token để gọi API này
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = UserLogin(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data["username"]
            password = serializer.validated_data["password"]
            
            # Kiểm tra user/pass
            user = authenticate(username=username, password=password)

            if user is not None:
                # 👇 TẠO HOẶC LẤY TOKEN CHO USER (Thay vì dùng session login)
                token, created = Token.objects.get_or_create(user=user)
                
                return Response(
                    {
                        "message": "Đăng nhập thành công!",
                        "token": token.key, # Trả về Token cho Frontend lưu
                        "user_id": user.id,
                        "username": user.username,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"error": "Tài khoản hoặc mật khẩu không đúng"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# View Cung cấp Database (Provisioning)
class ProvisionView(APIView):
    permission_classes = [IsAuthenticated]
    # 👇 BẮT BUỘC DÙNG TOKEN ĐỂ XÁC THỰC
    authentication_classes = [TokenAuthentication]

    def post(self, request):
        serializer = Provision(data=request.data)

        if serializer.is_valid():
            db_name = serializer.validated_data.get("db_name")
            db_password = serializer.validated_data["db_password"]

            if not db_name:
                db_name = f"{request.user.username}_{request.user.id}_db"

            success, result = create_database_and_user(
                db_name,
                db_password,
                request.user.id,
            )

            if success:
                # Lưu vào lịch sử Django
                try:
                    UserDatabase.objects.create(
                        user=request.user,
                        db_name=result["db_name"],
                        db_user=result["db_user"],
                        db_password=result["db_password"],
                    )
                    return Response(
                        {"message": "Tạo Database thành công!", "db_info": result},
                        status=status.HTTP_201_CREATED,
                    )
                except Exception as e:
                     return Response(
                        {"message": "Tạo MySQL thành công nhưng lỗi lưu log.", "details": str(e)},
                        status=status.HTTP_201_CREATED,
                    )
            else:
                return Response(
                    {
                        "error": "Lỗi hệ thống khi tạo Database.",
                        "details": result,
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# View liệt kê các Database của user hiện tại
class DatabaseListView(generics.ListAPIView):
    # 👇 Sửa lỗi chính tả: permission_classes (có chữ p)
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication] # Dùng Token
    serializer_class = UserDatabaseSerializer

    def get_queryset(self):
        return UserDatabase.objects.filter(user=self.request.user).order_by("-created_at")


# View Xóa Database
class DatabaseDeleteView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication] # Dùng Token

    def delete(self, request, pk):
        try:
            user_db = UserDatabase.objects.get(pk=pk, user=request.user)
            success, msg = delete_database_from_mysql(user_db.db_name)

            if success:
                user_db.delete()
                return Response(
                    {"message": "Đã xóa Database thành công!"},
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"error": "Lỗi MySQL: " + msg},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        except UserDatabase.DoesNotExist:
            return Response(
                {"error": "Không tìm thấy Database hoặc bạn không có quyền xóa."},
                status=status.HTTP_404_NOT_FOUND,
            )