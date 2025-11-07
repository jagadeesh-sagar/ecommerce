from . import views
from django.urls import path,include

urlpatterns=[
    
    path('product/',views.product_view,name='product-list'),
    path('product/create',views.product_create,name='product-create'),
    path('product/detail/<int:pk>',views.product_detail,name='product-detail'),
    path('product/search/',views.product_search_view,name='product-search'),
    path('product/image/<int:pk>',views.productImage_retrieve_view,name='product-image'),
    path('product/categories/',views.category_view,name='category-create'),
    path('product/qna/ans/<int:pk>',views.seller_ans,name='qna-ans'),
    path('product/qna/<int:pk>',views.customer_qxns,name='qna'),
    path('address/',views.address_create,name='address-create'),

]