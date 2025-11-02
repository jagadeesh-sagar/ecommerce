from rest_framework.views import APIView 
from rest_framework import generics,mixins,status
from rest_framework.response import Response
from django.db.models import Q
from . import models
from . import serializers
from django.contrib.auth.models import User


class ProductAPIView(APIView):
    queryset=models.Product.objects.all()

    def get(self,request):
        serializer=serializers.ProductSerializer(self.queryset.all(),many=True,context={'request':request})

        return Response(serializer.data)
    
    def post(self,request):
        serializer=serializers.ProductSerializer(data=request.data,context={'request':request})
        print(serializer)
        if serializer.is_valid():
             serializer.save()   
             return Response(serializer.data,status=status.HTTP_201_CREATED)
        
        return Response(serializer.error_messages,status=status.HTTP_400_BAD_REQUEST)

product_view=ProductAPIView.as_view()


# class ProductCreateGenericView(generics.CreateAPIView):
#     queryset = models.Product.objects.all()
#     serializer_class = serializers.ProductSerializer
# product_create=ProductCreateGenericView.as_view()


# class ProductDetailAPIView(APIView):
#    queryset=models.Product.objects.all()

#    def get(self,request,pk):
#      qs=generics.get_object_or_404(models.Product,id=pk)
#      serializer=serializers.ProductDetailSerializers(qs,many=True,context={'request':request})     
     
#      return Response(serializer.data)
   
# product_detail=ProductDetailAPIView.as_view()


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
        print(self.requst.user)
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