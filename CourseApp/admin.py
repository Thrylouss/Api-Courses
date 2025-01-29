from django.contrib import admin

from CourseApp.models import CustomUser, PhoneVerification, PasswordResetCode

admin.site.register([CustomUser, PhoneVerification, PasswordResetCode])