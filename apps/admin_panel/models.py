from django.db import models

class Category(models.Model):
    title = models.CharField(max_length=100, null=False, blank=False)


class SubCategory(models.Model):
    category_id = models.ForeignKey(Category, on_delete=models.CASCADE)
    title = models.CharField(max_length=100, null=False, blank=False)