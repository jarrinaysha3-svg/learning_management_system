from django.contrib.auth.models import User
from lms_app.models import *
from django import forms
from django.contrib.auth.forms import UserCreationForm


class RegistrationForm(UserCreationForm):
    email= forms.EmailField()
    name= forms.CharField(max_length=200)
    role= forms.ChoiceField(choices=UserProfileModel.ROLE_TYPES)

    class Meta:
        model= User
        fields= ['username','email','name','role','password1','password2']

    def save(self, commit=True):
        user= super().save(commit=commit)
        if commit:
            UserProfileModel.objects.create(
                user= user,
                name= self.cleaned_data['name'],
                role= self.cleaned_data['role'],
            )
        return user


class UpdateProfileForm(forms.ModelForm):
    email= forms.EmailField()

    class Meta:
        model= UserProfileModel
        fields= ['name','email','bio','image']


class CourseForm(forms.ModelForm):
    class Meta:
        model= CourseModel
        fields= ['category','title','description','thumbnail','level']


class LessonForm(forms.ModelForm):
    class Meta:
        model= LessonModel
        fields= ['title','lesson_type','video_url','file','content','order']

    def clean(self):
        cleaned_data= super().clean()
        lesson_type= cleaned_data.get('lesson_type')
        if lesson_type == 'Video' and not cleaned_data.get('video_url'):
            self.add_error('video_url', 'Video URL is required for a video lesson.')
        if lesson_type == 'Text' and not cleaned_data.get('content'):
            self.add_error('content', 'Content is required for a text lesson.')
        if lesson_type == 'File' and not (cleaned_data.get('file') or self.instance.file):
            self.add_error('file', 'Please upload a file for a file lesson.')
        return cleaned_data

class QuizForm(forms.ModelForm):
    class Meta:
        model= QuizModel
        fields= ['title','pass_mark']

    def clean_pass_mark(self):
        pass_mark= self.cleaned_data['pass_mark']
        if pass_mark > 100:
            raise forms.ValidationError('Pass mark cannot be more than 100.')
        return pass_mark


class QuestionForm(forms.Form):
    CORRECT_CHOICES=[
        ('1','Choice 1'),
        ('2','Choice 2'),
        ('3','Choice 3'),
        ('4','Choice 4'),
    ]
    text= forms.CharField(max_length=500, label='Question')
    choice_1= forms.CharField(max_length=300)
    choice_2= forms.CharField(max_length=300)
    choice_3= forms.CharField(max_length=300, required=False)
    choice_4= forms.CharField(max_length=300, required=False)
    correct= forms.ChoiceField(choices=CORRECT_CHOICES, label='Correct answer')

    def clean(self):
        cleaned_data= super().clean()
        correct= cleaned_data.get('correct')
        if correct and not cleaned_data.get(f'choice_{correct}'):
            raise forms.ValidationError('The correct answer cannot be an empty choice.')
        return cleaned_data


class ReviewForm(forms.ModelForm):
    class Meta:
        model= ReviewModel
        fields= ['rating','comment']