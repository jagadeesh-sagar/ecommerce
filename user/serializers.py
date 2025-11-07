from django.contrib.auth.models import User
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from rest_framework.response import Response
from . import models 
from inventory.models import Seller 
from django.db.models import Q
from django.utils import timezone


class CategorySerializers(serializers.ModelSerializer):
    class Meta:
        model=models.Category
        fields=['name','parent','origin','description']


class ProductImageSerializers(serializers.ModelSerializer):
    # product_name=serializers.CharField(source='product.name')
    class Meta:
        model = models.ProductImage
        fields = ['image_url', 'alt_text', 'video_url', 
                  'is_primary', 'display_order']
    

class ReviewSerializers(serializers.ModelSerializer):

    class Meta:
        model = models.Review
        fields = ['user','rating', 'review_text', 'review_image',
                  
                  'review_image','helpful_count']
    

class ProductVariantSerializers(serializers.ModelSerializer):
 
    class Meta:
        model=models.ProductVariant
        fields=['color','size','price','stock_qty']

    def get_product_name(self,obj):
       return obj.product.name
        

class CustomerQuestionSerializers(serializers.ModelSerializer):
  
    # product_name=serializers.CharField(source='product.name')  
    class Meta:
        model=models.QnA
        fields=['id','question','product']

    def create(self, validated_data):
        validated_data['user']=self.context['request'].user
        return super().create(validated_data)
    

class QnA(serializers.ModelSerializer):

    class Meta:
        model=models.QnA
        fields=['id','question','answer','product']

    def create(self, validated_data):
        validated_data['user']=self.context['request'].user
        return super().create(validated_data)
    

class ProductSearchSerializers(serializers.ModelSerializer):

    product_name=serializers.CharField(source="name")
    category_name=serializers.CharField(source='category.name',read_only=True)
    category=serializers.PrimaryKeyRelatedField(queryset=models.Category.objects.all(),write_only=True)
    brand_name=  serializers.CharField(source='brand.name',read_only=True)
    brand=serializers.PrimaryKeyRelatedField(queryset=models.Brand.objects.all(),write_only=True)
    seller_name=serializers.SerializerMethodField(read_only=True)
    variants=ProductVariantSerializers(many=True,read_only=True)
    seller=serializers.PrimaryKeyRelatedField(queryset=Seller.objects.all(),write_only=True)

    class Meta:
        model=models.Product
        fields=['seller','seller_name','product_name','category_name',
                'base_price','category','brand_name','variants','brand']

    def get_seller_name(self, obj):
       return obj.seller.user.username
    

class ProductDetailSerializers(serializers.ModelSerializer):

    product_name=serializers.CharField(source="name")
    category_name=serializers.CharField(source='category.name',read_only=True)
    category=serializers.PrimaryKeyRelatedField(queryset=models.Category.objects.all(),write_only=True)
    brand_name=  serializers.CharField(source='brand.name',read_only=True)
    brand=serializers.PrimaryKeyRelatedField(queryset=models.Brand.objects.all(),write_only=True)
    seller_name=serializers.SerializerMethodField(read_only=True)
    images=ProductImageSerializers(many=True,read_only=True)
    variants=ProductVariantSerializers(many=True,read_only=True)
    reviews=ReviewSerializers(many=True,read_only=True)
    seller=serializers.PrimaryKeyRelatedField(queryset=Seller.objects.all(),write_only=True)
    questions=QnA(many=True)

    class Meta:
        model=models.Product
        fields=['seller','seller_name','images','product_name','category_name'
                ,'description','base_price','category','brand_name',
            'brand','sku','is_active','images','variants','reviews','questions']

    def get_seller_name(self, obj):
       return obj.seller.user.username
    

class ProductCreateSerializers(serializers.ModelSerializer):

    product_name=serializers.CharField(source="name")
    category_name=serializers.CharField(source='category.name',read_only=True)
    brand_name=  serializers.CharField(source='brand.name',read_only=True)
    images=ProductImageSerializers(many=True)
    variants=ProductVariantSerializers(many=True,required=False)

    category = serializers.SlugRelatedField(
        slug_field='name',
        queryset=models.Category.objects.all()
    )
    brand = serializers.SlugRelatedField(
        slug_field='name',
        queryset=models.Brand.objects.all()
    )

    class Meta:
        model=models.Product
        fields=['images','product_name','category_name','description','base_price',
                'category','brand_name','brand','sku','is_active','images','variants',]

    def create(self, validated_data):
        image_data=validated_data.pop('images',[])
        variant_data=validated_data.pop('variants',[])

        user = self.context['request'].user
        seller=Seller.objects.get(user=user)
        validated_data['seller'] = seller

        product=models.Product.objects.create(**validated_data)

        for image in image_data:
            models.ProductImage.objects.create(product=product,**image)
        
        for variant in variant_data:
            models.ProductVariant.objects.create(product=product,**variant)

        return product
        
    
class ProductSerializer(serializers.ModelSerializer):

    product_name=serializers.CharField(source="name")
    category_name=serializers.CharField(source='category.name',read_only=True)
    category=serializers.PrimaryKeyRelatedField(queryset=models.Category.objects.all(),write_only=True)
    brand_name=  serializers.CharField(source='brand.name',read_only=True)
    brand=serializers.PrimaryKeyRelatedField(queryset=models.Brand.objects.all(),write_only=True)
    reviews=ReviewSerializers(many=True,read_only=True)     

    class Meta:
        model=models.Product
        fields=['product_name','description','category_name','base_price',
                'category','brand_name','brand','reviews']


class AddressSerializers(serializers.ModelSerializer):
    user=serializers.CharField(read_only=True)
    
    class Meta:
        model=models.Address
        fields=['user','address_type','house_no','street','city','state','country','postal_code','phone_number','other_number']

    def create(self, validated_data):
        validated_data['user']=self.context['request'].user
        return super().create(validated_data)
    

class SellerAnswersSerializers(serializers.ModelSerializer):
    
    question=serializers.CharField(read_only=True)
    class Meta:
        model=models.QnA
        fields=['id','answer','product','question']     

    def update(self,instance, validated_data):
        answered_by=self.context['request'].user
        instance.answered_by=answered_by
        if validated_data['answer']:
            instance.is_answered=True
        instance.answered_at=timezone.now()
   
        print(validated_data)
        return super().update(instance,validated_data)
    