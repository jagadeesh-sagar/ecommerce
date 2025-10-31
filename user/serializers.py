from django.contrib.auth.models import User
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from rest_framework.response import Response
from . import models 
from inventory.models import Seller 


class CategorySerializers(serializers.ModelSerializer):
    class Meta:
        model=models.Category
        fields=['name','parent','origin','description']


class ProductImageSerializers(serializers.ModelSerializer):
    # product_name=serializers.CharField(source='product.name')
    class Meta:
        model = models.ProductImage
        fields = ['image_url', 'alt_text', 'video_url', 'is_primary', 'display_order']
    

class ReviewSerializers(serializers.ModelSerializer):

    class Meta:
        model = models.Review
        fields = ['user','rating', 'review_text', 'review_image','review_image','helpful_count']
    

class ProductVariantSerializers(serializers.ModelSerializer):
 
    class Meta:
        model=models.ProductVariant
        fields=['color','size','price','stock_qty']

    def get_product_name(self,obj):
       return obj.product.name
        

class ProductSerializers(serializers.ModelSerializer):

    product_name=serializers.CharField(source="name")
    category_name=serializers.CharField(source='category.name',read_only=True)
    category=serializers.PrimaryKeyRelatedField(queryset=models.Category.objects.all(),write_only=True)
    brand_name=  serializers.CharField(source='brand.name',read_only=True)
    brand=serializers.PrimaryKeyRelatedField(queryset=models.Brand.objects.all(),write_only=True)
    seller_name=serializers.SerializerMethodField(read_only=True)
    images=ProductImageSerializers(many=True,read_only=True)
    variants=ProductVariantSerializers(many=True,read_only=True)
    reviews=ReviewSerializers(many=True,read_only=True)
    # seller=serializers.CharField(read_only=True)
    # product_images = serializers.SerializerMethodField()
    # product_variants = serializers.SerializerMethodField()
    seller=serializers.PrimaryKeyRelatedField(queryset=Seller.objects.all(),write_only=True)

    class Meta:
        model=models.Product
        fields=['seller','seller_name','images','product_name','category_name','description','base_price','category','brand_name','brand','sku','is_active','images','variants','reviews']


    def get_seller_name(self, obj):
       return obj.seller.user.username
    
