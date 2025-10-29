from django import forms
from .models import Post

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['content', 'photo']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter content'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
        }