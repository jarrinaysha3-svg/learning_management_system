from django.db import models

# Create your models here.
import uuid
from django.db import models
from django.db.models import Avg
from django.contrib.auth.models import User


class UserProfileModel(models.Model):
    ROLE_TYPES=[
        ('Student','Student'),
        ('Instructor','Instructor'),
    ]
    user= models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_profile', null=True)
    name= models.CharField(max_length=200, null=True)
    role= models.CharField(choices=ROLE_TYPES, max_length=30, default='Student')
    bio= models.TextField(null=True, blank=True)
    image= models.ImageField(upload_to='user_image', null=True, blank=True)

    def __str__(self):
        return f'{self.name}'


class CategoryModel(models.Model):
    name= models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f'{self.name}'


class CourseModel(models.Model):
    LEVEL_TYPES=[
        ('Beginner','Beginner'),
        ('Intermediate','Intermediate'),
        ('Advanced','Advanced'),
    ]
    STATUS_TYPES=[
        ('Pending','Pending'),
        ('Approved','Approved'),
        ('Rejected','Rejected'),
    ]
    instructor= models.ForeignKey(User, on_delete=models.CASCADE, related_name='instructor_courses', null=True)
    category= models.ForeignKey(CategoryModel, on_delete=models.SET_NULL, related_name='category_courses', null=True, blank=True)
    title= models.CharField(max_length=200, null=True)
    description= models.TextField(null=True)
    thumbnail= models.ImageField(upload_to='course_thumbnail', null=True, blank=True)
    level= models.CharField(choices=LEVEL_TYPES, max_length=30, default='Beginner')
    approval_status= models.CharField(choices=STATUS_TYPES, max_length=30, default='Pending')
    created_at= models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering= ['-created_at']

    def __str__(self):
        return f'{self.title}'

    def lesson_count(self):
        return self.lessons.count()

    def enrolled_count(self):
        return self.enrollments.count()

    def average_rating(self):
        avg= self.reviews.aggregate(avg_rating= Avg('rating'))['avg_rating']
        return round(avg, 1) if avg else 0


class LessonModel(models.Model):
    LESSON_TYPES=[
        ('Video','Video'),
        ('File','File'),
        ('Text','Text'),
    ]
    course= models.ForeignKey(CourseModel, on_delete=models.CASCADE, related_name='lessons', null=True)
    title= models.CharField(max_length=200, null=True)
    lesson_type= models.CharField(choices=LESSON_TYPES, max_length=30, default='Video')
    video_url= models.URLField(null=True, blank=True)
    file= models.FileField(upload_to='lesson_file', null=True, blank=True)
    content= models.TextField(null=True, blank=True)
    order= models.PositiveIntegerField(default=1)

    class Meta:
        ordering= ['order', 'id']

    def __str__(self):
        return f'{self.course.title}-{self.title}'

    def embed_url(self):
        url= self.video_url or ''
        if 'watch?v=' in url:
            return url.replace('watch?v=', 'embed/').split('&')[0]
        if 'youtu.be/' in url:
            return url.replace('youtu.be/', 'www.youtube.com/embed/').split('?')[0]
        return url


class EnrollmentModel(models.Model):
    student= models.ForeignKey(User, on_delete=models.CASCADE, related_name='student_enrollments', null=True)
    course= models.ForeignKey(CourseModel, on_delete=models.CASCADE, related_name='enrollments', null=True)
    enrolled_at= models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together= ['student', 'course']
        ordering= ['-enrolled_at']

    def __str__(self):
        return f'{self.student.username}-{self.course.title}'

    def completed_lesson_count(self):
        return LessonProgressModel.objects.filter(
            student=self.student, lesson__course=self.course, is_completed=True
        ).count()

    def progress(self):
        total= self.course.lessons.count()
        if total == 0:
            return 0
        return round((self.completed_lesson_count() / total) * 100)


class LessonProgressModel(models.Model):
    student= models.ForeignKey(User, on_delete=models.CASCADE, related_name='lesson_progress', null=True)
    lesson= models.ForeignKey(LessonModel, on_delete=models.CASCADE, related_name='progress', null=True)
    is_completed= models.BooleanField(default=True)
    completed_at= models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together= ['student', 'lesson']

    def __str__(self):
        return f'{self.student.username}-{self.lesson.title}'


class QuizModel(models.Model):
    course= models.ForeignKey(CourseModel, on_delete=models.CASCADE, related_name='quizzes', null=True)
    title= models.CharField(max_length=200, null=True)
    pass_mark= models.PositiveIntegerField(default=50, help_text='Pass percentage (0-100)')

    def __str__(self):
        return f'{self.course.title}-{self.title}'


class QuestionModel(models.Model):
    quiz= models.ForeignKey(QuizModel, on_delete=models.CASCADE, related_name='questions', null=True)
    text= models.CharField(max_length=500, null=True)

    def __str__(self):
        return f'{self.text}'


class ChoiceModel(models.Model):
    question= models.ForeignKey(QuestionModel, on_delete=models.CASCADE, related_name='choices', null=True)
    text= models.CharField(max_length=300, null=True)
    is_correct= models.BooleanField(default=False)

    def __str__(self):
        return f'{self.text}'


class QuizAttemptModel(models.Model):
    student= models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts', null=True)
    quiz= models.ForeignKey(QuizModel, on_delete=models.CASCADE, related_name='attempts', null=True)
    score= models.PositiveIntegerField(default=0)
    total= models.PositiveIntegerField(default=0)
    passed= models.BooleanField(default=False)
    attempted_at= models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering= ['-attempted_at']

    def __str__(self):
        return f'{self.student.username}-{self.quiz.title}-{self.score}/{self.total}'

    def percentage(self):
        if self.total == 0:
            return 0
        return round((self.score / self.total) * 100)

    def save(self, *args, **kwargs):
        self.passed= self.percentage() >= self.quiz.pass_mark
        super().save(*args, **kwargs)


class ReviewModel(models.Model):
    RATING_TYPES=[(i, i) for i in range(1, 6)]
    student= models.ForeignKey(User, on_delete=models.CASCADE, related_name='student_reviews', null=True)
    course= models.ForeignKey(CourseModel, on_delete=models.CASCADE, related_name='reviews', null=True)
    rating= models.PositiveSmallIntegerField(choices=RATING_TYPES, default=5)
    comment= models.TextField(null=True, blank=True)
    created_at= models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together= ['student', 'course']
        ordering= ['-created_at']

    def __str__(self):
        return f'{self.student.username}-{self.course.title}-{self.rating}'


class CertificateModel(models.Model):
    student= models.ForeignKey(User, on_delete=models.CASCADE, related_name='student_certificates', null=True)
    course= models.ForeignKey(CourseModel, on_delete=models.CASCADE, related_name='certificates', null=True)
    certificate_id= models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    issued_at= models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together= ['student', 'course']

    def __str__(self):
        return f'{self.student.username}-{self.course.title}'