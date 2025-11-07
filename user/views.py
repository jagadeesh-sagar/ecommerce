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
    lookup_field='pk'
customer_qxns=CustomerQuestion.as_view()
