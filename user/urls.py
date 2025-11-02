from . import views
from django.urls import path,include

urlpatterns=[
    
    path('product/',views.product_view,name='product-list'),
    # path('product/create',views.product_create,name='product-create'),
    path('product/detail/<int:pk>',views.product_detail,name='product-detail'),
    path('product/search/',views.product_search_view,name='product-search'),
    path('product/image/<int:pk>',views.productImage_retrieve_view,name='product-image'),
    # path('update/',views.product_update_view,name='product-update'),
]