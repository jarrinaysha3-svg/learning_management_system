from django.contrib import admin
from lms_app.models import *

admin.site.register([UserProfileModel, CategoryModel, CourseModel, LessonModel, EnrollmentModel, LessonProgressModel, QuizModel, QuestionModel, ChoiceModel, QuizAttemptModel, ReviewModel, CertificateModel])