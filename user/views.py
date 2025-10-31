from rest_framework.views import APIView 
from rest_framework import generics
from rest_framework.response import Response
from django.db.models import Q
from . import models
from . import serializers
from django.contrib.auth.models import User

# class ProductListAPIView(generics.ListCreateAPIView):
#     queryset = models.Product.objects.all()
#     serializer_class=serializers.ProductSerializers

#     def get_queryset(self):
#         return super().get_queryset()

# product_list_create_view=ProductListAPIView.as_view()

# class ProductUpdateAPIview(generics.UpdateAPIView):
#     queryset = models.Product.objects.all()
#     serializer_class=serializers.ProductSerializers
     
#     def perform_update(self, serializer):
#         return super().perform_update(serializer)

# product_update_view=ProductUpdateAPIview.as_view()


# class ProductListAPIView(APIView):
#       # queryset = models.Product.objects.all()
#       serializer_class=serializers.ProductSerializers
  
#       def get(self,request,pk):
#           # user=self.request.user
#           queryset = models.Product.objects.all()
#           qs=queryset.filter(Q(name='lipstick'))
#           print(qs)
#         #   username=User.objects.get(user=user)
#         #   print(username)
#         #   print(request)
#           serializer=serializers.ProductSerializers(qs,many=True,context={'request':request})
#           # print(serializer)
#           print(serializer.data)
#           return Response(serializer.data)
# product_list_create_view=ProductListAPIView.as_view()


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
            queryset=queryset.filter(Q(name__icontains=name)) 

        if brand:
            queryset=queryset.filter(Q(brand__icontains=brand)) 

        if category:
            queryset=queryset.filter(Q(category=category)) 
        
        if  price is not None and price.isdigit():
                value=int(price)
                queryset=queryset|self.queryset.filter(Q(base_price=value)|Q(base_price__lte=value+1000))

        serializer=serializers.ProductSerializers(queryset,many=True,context={'request':request})

        return Response(serializer.data)
product_search_view=ProductSearch.as_view()


class ProductImageListview(generics.RetrieveAPIView):
    queryset = models.ProductImage.objects.all()
    serializer_class=serializers.ProductImageSerializers

productImage_retrieve_view=ProductImageListview.as_view()