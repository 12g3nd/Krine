import uuid
from django.db import models

class Post(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content = models.TextField(blank=True)
    image = models.ImageField(upload_to='posts/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Simple way to track if it's flagged by AI
    is_flagged = models.BooleanField(default=False)

    def __str__(self):
        return f"Post {self.id}..."

    @property
    def comment_count(self):
        return self.comments.count()

    @property
    def like_count(self):
        return self.reactions.filter(reaction_type='like').count()

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    posts = models.ManyToManyField(Post, related_name='tags')

    def __str__(self):
        return self.name

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment on {self.post.id}"

class Reaction(models.Model):
    LIKE = 'like'
    REACTION_CHOICES = [
        (LIKE, 'Like'),
    ]

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reactions')
    reaction_type = models.CharField(max_length=10, choices=REACTION_CHOICES, default=LIKE)
    # Store session_key or hash of IP/UserAgent for basic anon tracking
    session_id = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'session_id', 'reaction_type')
