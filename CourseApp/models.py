from django.utils.timezone import now, timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Count


# Create your models here.
class CustomUser(AbstractUser):
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    passport_number = models.CharField(max_length=255, null=True, blank=True)
    image = models.ImageField(upload_to='user_images/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)


class PhoneVerification(models.Model):
    phone_number = models.CharField(max_length=15, unique=True)
    password = models.CharField(max_length=32)
    verification_code = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.phone_number} - {self.verification_code}"


class PasswordResetCode(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="password_reset_codes")
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        # Код действует 10 минут
        return now() > self.created_at + timedelta(minutes=10)


class Category(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Skills(models.Model):
    name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='skills')

    def __str__(self):
        return self.name


class EducationCentres(models.Model):
    name = models.CharField(max_length=255)
    skills = models.ManyToManyField(Skills, blank=True, related_name='education_centres')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='education_centres')

    logo = models.ImageField(upload_to='education_centres/', null=True, blank=True)
    header_image = models.ImageField(upload_to='education_centres/', null=True, blank=True)

    # Если рейтинг может быть 0.00 и до 999.99, max_digits=5, decimal_places=2 — это 999.99.
    # Если нужен другой диапазон, скорректируйте
    rate = models.DecimalField(max_digits=5, decimal_places=2)
    rate_count = models.IntegerField(default=0)

    description = models.TextField()
    graduates = models.IntegerField()
    experience = models.IntegerField()
    employees = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    # Дополнительно (не обязательно):
    # Если хотите быстро получать количество филиалов:
    @property
    def num_branches(self):
        return self.branches.count()


class Branches(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    # Если нужна более точная широта/долгота, используйте DecimalField
    longitude = models.FloatField()
    latitude = models.FloatField()

    education_centre = models.ForeignKey(
        EducationCentres,
        on_delete=models.CASCADE,
        related_name='branches'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Courses(models.Model):
    name = models.CharField(max_length=255)
    duration = models.IntegerField()  # Уточните, в каких единицах (дни, часы, недели)
    rate = models.DecimalField(max_digits=5, decimal_places=2)

    price_month = models.IntegerField()  # Или DecimalField, если нужны дробные значения
    full_price = models.IntegerField()
    discount = models.IntegerField(default=0)  # процент скидки?

    description = models.TextField()

    image_one = models.ImageField(upload_to='courses/', null=True, blank=True)
    image_two = models.ImageField(upload_to='courses/', null=True, blank=True)

    EDUCATION_TYPES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('hybrid', 'Hybrid'),
    ]
    education_type = models.CharField(max_length=255, choices=EDUCATION_TYPES)

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='courses')
    education_centre = models.ForeignKey(EducationCentres, on_delete=models.CASCADE, related_name='courses')

    skills = models.ManyToManyField(Skills, blank=True, related_name='courses')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
