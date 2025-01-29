import datetime
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import *


User = get_user_model()


def normalize_phone_number(phone_number):
    """Удаляет плюс из номера телефона, если он присутствует."""
    return phone_number.lstrip('+') if phone_number else phone_number


class UserLogin(APIView):
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data.get("username")
            password = serializer.validated_data.get("password")
            print(username, password)
            # Ищем пользователя по username
            try:
                user = CustomUser.objects.get(username=username)
                # Генерируем токены
                if check_password(password, user.password):
                    refresh = RefreshToken.for_user(user)
                    return Response(
                        {
                            'refresh': str(refresh),
                            'access': str(refresh.access_token)
                        },
                        status=status.HTTP_200_OK
                    )
            except CustomUser.DoesNotExist:
                return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserRegister(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            phone_number = normalize_phone_number(serializer.validated_data["phone_number"])
            password = serializer.validated_data["password"]

            # Если пользователь с таким номером уже существует — выбрасываем ValidationError
            if CustomUser.objects.filter(username=phone_number).exists():
                raise ValidationError({'error': 'User with this phone number already exists'})
            elif len(password) < 8:
                return Response(
                    {"error": "Новый пароль должен содержать не менее 8 символов."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            else:
                serializer.validated_data["phone_number"] = phone_number  # Сохраняем номер без плюса
                phone = serializer.save()

            return Response(
                {
                    'code': phone.verification_code
                },
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetVerificationCode(viewsets.ModelViewSet):
    queryset = PhoneVerification.objects.all()
    serializer_class = PhoneVerificationSerializer

    @action(detail=False, methods=['post'])
    def verify_phone(self, request):
        print(request.data)
        phone_number = normalize_phone_number(request.data.get('phone_number'))
        print(phone_number)

        # Проверяем, что номер телефона указан
        if not phone_number:
            # Вместо возврата Response поднимаем исключение
            raise ValidationError("Номер телефона обязателен.")

        # Проверяем наличие номера в базе
        try:
            phone_verification = PhoneVerification.objects.get(phone_number=phone_number)
        except PhoneVerification.DoesNotExist:
            # Поднимаем исключение NotFound (вернёт 404 по умолчанию)
            raise NotFound("Номер телефона не найден.")

        # Проверяем, не верифицирован ли уже номер
        if phone_verification.is_verified:
            # Можно использовать ValidationError (400) или другое, в зависимости от логики
            raise ValidationError("Номер телефона уже подтвержден.")

        # Если прошло больше 5 минут — генерируем новый код
        if (phone_verification.created_at + datetime.timedelta(minutes=5)) < timezone.now():
            phone_verification.verification_code = generate_verification_code()
            phone_verification.created_at = timezone.now()
            phone_verification.save()

        return Response(
            {
                "message": "Код подтверждения отправлен.",
                "verification_code": phone_verification.verification_code
            },
            status=status.HTTP_200_OK
        )


class VerifyCode(APIView):
    def post(self, request):
        serializer = VerifyCodeSerializer(data=request.data)
        if serializer.is_valid():
            phone_number = normalize_phone_number(serializer.validated_data["phone_number"])
            verification_code = serializer.validated_data["verification_code"]
            try:
                phone = PhoneVerification.objects.get(phone_number=phone_number, verification_code=verification_code)
                phone.is_verified = True
                phone.save()
                password = make_password(phone.password)
                user = CustomUser.objects.create(username=phone_number, password=password)
                user.save()
                return Response({"message": "Phone number verified successfully"}, status=status.HTTP_200_OK)
            except PhoneVerification.DoesNotExist:
                return Response({"message": "Invalid verification code"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UpdateUserData(APIView):
    permission_classes = [IsAuthenticated]  # Проверяем, авторизован ли пользователь

    def put(self, request):
        user = request.user  # Получаем текущего пользователя из JWT-токена
        serializer = UpdateUserSerializer(user, data=request.data, partial=True)  # partial=True: позволяет обновлять только переданные поля

        if serializer.is_valid():
            try:
                serializer.save()  # Сохраняем изменения
                return Response({
                    "message": "Данные успешно обновлены",
                    "user": serializer.data
                }, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"error": f"Ошибка при сохранении данных: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    """
    API для смены пароля пользователя.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user  # Получаем текущего авторизованного пользователя
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        # Проверка, что все данные переданы
        if not old_password or not new_password or not confirm_password:
            return Response(
                {"error": "Необходимо указать старый пароль, новый пароль и его подтверждение."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Проверка старого пароля
        if not check_password(old_password, user.password):
            return Response(
                {"error": "Старый пароль указан неверно."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Проверка совпадения нового пароля и его подтверждения
        if new_password != confirm_password:
            return Response(
                {"error": "Новый пароль и его подтверждение не совпадают."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Применение дополнительной валидации для нового пароля
        if len(new_password) < 8:
            return Response(
                {"error": "Новый пароль должен содержать не менее 8 символов."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Смена пароля
        user.set_password(new_password)
        user.save()

        return Response({"message": "Пароль успешно изменён."}, status=status.HTTP_200_OK)


class RequestPasswordResetView(APIView):
    """
    Запрос на сброс пароля: создаёт и отправляет код подтверждения.
    """
    def post(self, request):
        serializer = RequestPasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            user = User.objects.get(username=phone_number)

            # Удаляем старые коды для пользователя
            PasswordResetCode.objects.filter(user=user, is_used=False).delete()

            # Генерируем новый код
            reset_code = PasswordResetCode.objects.create(
                user=user,
                code=str(random.randint(100000, 999999))
            )

            # Имитация отправки кода (например, через SMS)
            print(f"Отправленный код для {phone_number}: {reset_code.code}")

            return Response({"message": "Код для сброса пароля отправлен."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyResetCodeView(APIView):
    """
    Проверка кода сброса пароля.
    """
    def post(self, request):
        serializer = VerifyResetCodeSerializer(data=request.data)
        if serializer.is_valid():
            reset_code = serializer.validated_data['reset_code']
            return Response({"message": "Код подтверждён."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordView(APIView):
    """
    Сброс пароля с использованием кода подтверждения.
    """
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Пароль успешно сброшен."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)