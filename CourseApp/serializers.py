import re
import random
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from rest_framework import serializers

from CourseApp.models import CustomUser, PhoneVerification, PasswordResetCode, Category, Skills, EducationCentres, \
    Branches, Courses

User = get_user_model()


# 1) Создание пользователя напрямую (без SMS-подтверждения). Пароль сразу хешируем.
class UserRegisterSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def create(self, validated_data):
        # Хешируем пароль
        validated_data['password'] = make_password(validated_data['password'])
        user = CustomUser.objects.create(**validated_data)
        return user


# 2) Логин: простая схема — получает username/password
class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


# 3) Обновление полей пользователя (без пароля)
class UpdateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'date_of_birth', 'passport_number', 'image']
        extra_kwargs = {
            'date_of_birth': {'required': False},
            'passport_number': {'required': False},
            'first_name': {'required': False},
            'last_name': {'required': False},
            'image': {'required': False},
        }

    def validate_date_of_birth(self, value):
        if value and value.year < 1900:
            raise serializers.ValidationError("Год рождения не может быть меньше 1900.")
        return value

    def validate_passport_number(self, value):
        uzb_passport_pattern = r'^[A-Z]{2}\d{7}$'
        if not re.match(uzb_passport_pattern, value):
            raise serializers.ValidationError(
                "Номер паспорта должен состоять из 2 латинских заглавных букв и 7 цифр (например, AB1234567)."
            )
        # Проверка уникальности
        if User.objects.filter(passport_number=value).exists():
            raise serializers.ValidationError("Этот номер паспорта уже используется.")
        return value


# Генерация 6-значного кода
def generate_verification_code():
    return str(random.randint(100000, 999999))


# 4) Регистрация с помощью телефона (через модель PhoneVerification).
#    Пароль не хешируем в PhoneVerification, чтобы потом на этапе VerifyCode
#    взять исходный пароль и создать пользователя в CustomUser уже с хешированием.
class RegisterSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    password = serializers.CharField(write_only=True)

    def create(self, validated_data):
        verification_code = generate_verification_code()

        # Ищем или создаём запись в PhoneVerification
        phone_verification, created = PhoneVerification.objects.get_or_create(
            phone_number=validated_data['phone_number']
        )
        # Если запись уже была, вы можете решить, что делать:
        # - Перезаписать пароль и verification_code,
        # - Или выбросить ошибку, если не хотим несколько раз пересылать.

        phone_verification.password = validated_data['password']  # в открытом виде!
        phone_verification.verification_code = verification_code
        phone_verification.is_verified = False  # Сбрасываем в false, если пересоздаём код
        phone_verification.save()
        return phone_verification


# 5) Посмотреть поля PhoneVerification (если нужно)
class PhoneVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhoneVerification
        fields = '__all__'


# 6) Сериализатор для проверки кода
class VerifyCodeSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    verification_code = serializers.CharField(max_length=6)


# 7) Запрос на сброс пароля
class RequestPasswordResetSerializer(serializers.Serializer):
    phone_number = serializers.CharField()

    def validate_phone_number(self, value):
        if not User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Пользователь с таким номером телефона не найден.")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)


# 8) Проверяем код для сброса пароля
class VerifyResetCodeSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    code = serializers.CharField(max_length=6)

    def validate(self, data):
        try:
            reset_code = PasswordResetCode.objects.get(
                user__username=data['phone_number'],
                code=data['code'],
                is_used=False
            )
        except PasswordResetCode.DoesNotExist:
            raise serializers.ValidationError("Неверный или уже использованный код.")

        if reset_code.is_expired():
            raise serializers.ValidationError("Код истёк.")

        data['reset_code'] = reset_code
        return data


# 9) Установка нового пароля по коду
class ResetPasswordSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    code = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True)

    def validate(self, data):
        try:
            reset_code = PasswordResetCode.objects.get(
                user__username=data['phone_number'],
                code=data['code'],
                is_used=False
            )
        except PasswordResetCode.DoesNotExist:
            raise serializers.ValidationError("Неверный или уже использованный код.")

        if reset_code.is_expired():
            raise serializers.ValidationError("Код истёк.")

        data['user'] = reset_code.user
        return data

    def save(self):
        user = self.validated_data['user']
        user.password = make_password(self.validated_data['new_password'])
        user.save()

        # Помечаем код как использованный
        reset_code = PasswordResetCode.objects.get(
            user=user, code=self.validated_data['code']
        )
        reset_code.is_used = True
        reset_code.save()


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skills
        fields = '__all__'


class EducationCentresSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationCentres
        fields = '__all__'


class BranchesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branches
        fields = '__all__'


class CoursesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Courses
        fields = '__all__'
