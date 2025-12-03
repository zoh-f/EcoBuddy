from django import forms
from .models import Profile, Post

class ProfileImageForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["profile_picture"]

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content', 'photo', 'topic', 'privacy', 'hashtags', 'is_draft']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter title'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Share your sustainability journey...', 'rows': 8}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
            'topic': forms.Select(attrs={'class': 'form-control'}),
            'privacy': forms.RadioSelect(),
            'hashtags': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter hashtags separated by commas for further reach!'}),
            'is_draft': forms.CheckboxInput(),
        }