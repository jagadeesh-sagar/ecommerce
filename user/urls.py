from . import views
from django.urls import path,include

urlpatterns=[


    # path('product/<int:pk>',views.product_list_create_view,name='product-list'),
    path('product_search/',views.product_search_view,name='product-search'),
    path('product_image/<int:pk>',views.productImage_retrieve_view,name='product-image'),
    # path('update/',views.product_update_view,name='product-update'),
]