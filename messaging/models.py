from django.db import models

# Create your models here.
 
class Author(models.Model):
    name = models.CharField(max_length=500)
 
class Message(models.Model):
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)