from django import forms
from .models import Post, Comment

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['content', 'post_type']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-input post-content-input', 'placeholder': 'Share your thought...', 'rows': 5}),
            'post_type': forms.Select(attrs={'class': 'form-input post-type-select'}),
        }

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-input comment-input', 'placeholder': 'Add a comment...', 'rows': 3}),
        }
