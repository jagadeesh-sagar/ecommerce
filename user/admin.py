from django.contrib import admin
from .models import Payment,Product,Brand,Category,ProductVariant,ProductImage,Review,Order,OrderItem
from inventory import models


admin.site.register(Product)
admin.site.register(Category)
admin.site.register(Brand)
admin.site.register(models.Seller)
admin.site.register(ProductVariant) 
admin.site.register(ProductImage)
admin.site.register(Review)
admin.site.register(Order)
admin.site.register(OrderItem)