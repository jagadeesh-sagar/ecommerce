from rest_framework.views import APIView 
from rest_framework import generics,mixins,status
from rest_framework.response import Response
from django.db.models import Q
from . import models
from . import serializers
from django.contrib.auth.models import User
from inventory.models import Seller
from django.shortcuts import get_object_or_404


class ProductAPIView(APIView):
    queryset=models.Product.objects.all()

    def get(self,request):
        serializer=serializers.ProductSerializer(self.queryset.all(),many=True,context={'request':request})

        return Response(serializer.data)
    
    def post(self,request):
        serializer=serializers.ProductCreateSerializers(data=request.data,context={'request':request})
        if serializer.is_valid():
             serializer.save()   
             return Response(serializer.data,status=status.HTTP_201_CREATED)
        
        return Response(serializer.error_messages,status=status.HTTP_400_BAD_REQUEST)

product_view=ProductAPIView.as_view()


class ProductCreateGenericView(generics.CreateAPIView):
    queryset = models.Product.objects.all()
    serializer_class = serializers.ProductCreateSerializers
product_create=ProductCreateGenericView.as_view()


class ProductDetailView(mixins.RetrieveModelMixin,generics.GenericAPIView):

    queryset=models.Product.objects.all()
    serializer_class=serializers.ProductDetailSerializers
    lookup_field='pk'

    def get(self,request,*args,**kwargs):
        return self.retrieve(request,*args,**kwargs)
    
product_detail=ProductDetailView.as_view()


class ProductSearch(APIView):
     queryset=models.Product.objects.all()

     def get_serializer_context(self):
        context = super().get_serializer_context()
        context['user'] = self.request.user
        return context
        
     def get(self,request):
        category=self.request.GET.get('ct',None)
        name=self.request.GET.get('n',None)
        brand=self.request.GET.get('b',None)
        price=self.request.GET.get('p',None)
        queryset=self.queryset.all()

        if name:
            queryset=queryset.filter(Q(product__name__icontains=name)) 

        if brand:
            queryset=queryset.filter(Q(brand__name__icontains=brand)) 

        if category:
            queryset=queryset.filter(Q(category__name__icontains=category)) 
        
        if  price is not None and price.isdigit():
                value=int(price)
                queryset=queryset|self.queryset.filter(Q(base_price=value)|Q(base_price__lte=value+1000))

        serializer=serializers.ProductSearchSerializers(queryset,many=True,context={'request':request})

        return Response(serializer.data)
product_search_view=ProductSearch.as_view()


class ProductImageListview(generics.RetrieveAPIView):
    queryset = models.ProductImage.objects.all()
    serializer_class=serializers.ProductImageSerializers

productImage_retrieve_view=ProductImageListview.as_view()


class AddressView(generics.ListCreateAPIView):
    queryset = models.Address.objects.all()
    serializer_class = serializers.AddressSerializers
address_create=AddressView.as_view()


class CategoryListCreateview(generics.ListCreateAPIView):
    queryset = models.Category.objects.all()
    serializer_class = serializers.CategorySerializers
category_view=CategoryListCreateview.as_view()


class SellerAnswers(APIView):
   
    def get_queryset(self):
        try:
            seller=Seller.objects.get(user=self.request.user)
            print(seller)
            return models.QnA.objects.filter(product__seller=seller)
        except Seller.DoesNotExist:
           return models.QnA.objects.none()

    def get(self,request,*args,**kwargs):
        pk=kwargs['pk']
        question=get_object_or_404(self.get_queryset(),id=pk)
        serializer=serializers.SellerAnswersSerializers(question,context={'request':request})
        return Response(serializer.data)
    
    def patch(self,request,*args,**kwargs):
        pk=kwargs['pk']
        question=get_object_or_404(self.get_queryset(),id=pk)
        serializer=serializers.SellerAnswersSerializers(question,data=request.data,partial=True,context={'request':request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

seller_ans=SellerAnswers.as_view()


class CustomerQuestion(generics.CreateAPIView):
    queryset=models.QnA.objects.all()
    serializer_class=serializers.CustomerQuestionSerializers

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['id'] = self.request.GET.get('q')
        return context
    
customer_qxns=CustomerQuestion.as_view()


class CartItem(APIView):
   

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['user'] = self.request.user
        return context
  
    def get(self,request):
        cart=models.Cart.objects.get_or_create(user=self.request.user)
        cartitem=models.CartItem.objects.filter(Q(cart__user=cart[0].user))
        serializer=serializers.CartItemRetrieveSerializers(cartitem,many=True,context={'request':request})
        return Response(serializer.data)

    def post(self,request):

        product_id=request.GET.get('product')
        variant_id=request.GET.get('variant')
        
        if not product_id:
            return Response({"error":"product is required"},status=400)
        cart,_=models.Cart.objects.get_or_create(user=request.user)

        cart_item=models.CartItem.objects.filter(
            cart=cart,
            product_id=product_id,
            product_variant_id=variant_id if variant_id !="0" else None).first()
        
        if cart_item:

            cart_item.quantity+=int(request.data.get("quantity",1))
            if cart_item.quantity<=0:
                cart_item.delete()
                return Response({"message":"Item removed from cart"},status=200)
            
            cart_item.save()
            serializer=serializers.CartItemRetrieveSerializers(cart_item)
            return Response(
                {"message":"Updated quantity","item":serializer.data},
                status=200
            )

        serializer=serializers.CartItemCreateSerializers(data=request.data,
                                                         context={'request':request,'product':int(product_id),'variant':int(variant_id) if variant_id else 0,})
    
        if serializer.is_valid():  
            cart_item=serializer.save() 
            output=serializers.CartItemRetrieveSerializers(cart_item).data

            return Response(
            {"message": "Item added", "item": output},
            status=status.HTTP_201_CREATED)
        
        return Response(serializer.error_messages,status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self,request):
        
        product_id=request.GET.get('product')
        variant_id=request.GET.get('variant')
        if not product_id:
            return Response({"error":"product is required"},status=400)
        cart=models.Cart.objects.get(user=request.user)

        cart_item=models.CartItem.objects.filter(
            cart=cart,
            product_id=product_id,
            product_variant_id=variant_id if variant_id !="0" else None)
        cart_item.delete()

        return Response(
                {"message":"deleted succefully"},
                status=200
            )
              
cartitem=CartItem.as_view()
    
        

        