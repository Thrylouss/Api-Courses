from django.contrib import admin

from CourseApp.models import *

admin.site.register([CustomUser, PhoneVerification, PasswordResetCode, EducationCentres, Branches, Courses, Category,
                     Skills])