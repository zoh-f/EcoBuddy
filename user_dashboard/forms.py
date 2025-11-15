from django import forms
from .models import Profile, Post

class ProfileImageForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["profile_picture"]

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content', 'photo']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter title'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter content'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
        }