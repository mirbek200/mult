from django.urls import path
from .views import (
    CategoryListView, CategoryDetailView, CategoryCreateView,
    SubCategoryListView, SubCategoryDetailView, SubCategoryCreateView,
)

urlpatterns = [
    path('categories_list/', CategoryListView.as_view(), name='category-list'),
    path('categories_create/', CategoryCreateView.as_view(), name='category-create'),
    path('categories_detail/<int:pk>/', CategoryDetailView.as_view(), name='category-detail'),

    path('sub_categories_list/', SubCategoryListView.as_view(), name='sub_categories_list'),
    path('sub_categories_create/', SubCategoryCreateView.as_view(), name='sub_categories_create'),
    path('sub_categories_detail/<int:pk>/', SubCategoryDetailView.as_view(), name='sub_categories_detail '),

]
