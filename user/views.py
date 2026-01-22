from rest_framework.views import APIView
from rest_framework import generics,mixins,status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from . import models
from . import serializers
from django.contrib.auth.models import User
from inventory.models import Seller
from django.shortcuts import get_object_or_404
import boto3
from django.conf import settings


class ProductsListAPIView(APIView):
    '''
    Products List API

    Allows all users (Aunthenticated or not) to:

    - List all available Products  
    '''

    queryset=models.Product.objects.all()

    def get(self,request):
        '''
        Retrieve all available products

        Access:
            public
        Response:
            200 ok -List of products
        '''

        serializer=serializers.ProductSerializer(self.queryset.all(),many=True,context={'request':request})

        return Response(serializer.data,status=status.HTTP_200_OK)


product_view=ProductsListAPIView.as_view()


class ProductCreateGenericView(APIView):

    '''
    Docstring for Product Create API

    Allows Authenticated and Verified Sellers to:

    -Create or List a New Product

    sideEffects:
        - publishes SNS notification after Product creation
    '''
    permission_classes = [IsAuthenticated]

    sns_client=boto3.client("sns",aws_access_key_id = settings.AWS_ACCESS_KEY_ID,
                           aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                           region_name=settings.AWS_S3_REGION_NAME)
    SNS_TOPIC_ARN=settings.AWS_SNS_ARN
    
    def sns_publish(self,message,user):
        '''
        Publishes a AWS SNS Notification after creation of New Product
 
        :param message: Product name
        :param user: Seller creating Product
        '''
        self.sns_client.publish(TopicArn=self.SNS_TOPIC_ARN,
                                Message=f'$Mr.{user.username} you added {message}',
                                Subject="seller created product",)

    def post(self,request):
        '''
        Create a New Product
        
        Request Body:

        Workflow:
            1.Validate request data
            2.Save Product
            3.SNS Publish
        
        Responses:
            201: Product created
            400: Validation Error
        '''
        serializer=serializers.ProductCreateSerializers(data=request.data,
                                                        context={'request':request})
        if serializer.is_valid():
            product=serializer.save()

            #notify other systems async
            self.sns_publish(product.name,self.request.user)

            return Response(serializer.data,status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
            

product_create=ProductCreateGenericView.as_view()


class ProductDetailView(mixins.RetrieveModelMixin,generics.GenericAPIView):
    '''
     Product Detail API
     
     Allows all Users(Authenticated or not) to:
     - List details of a Product

    '''

    queryset=models.Product.objects.all()
    serializer_class=serializers.ProductDetailSerializers
    lookup_field='pk'

    def get(self,request,*args,**kwargs):
        '''
        Returns the details of a Product using:
            :param args: Product ID

        Access:
            public
        Response:
            200 ok -details of a Product 
        '''
        return self.retrieve(request,*args,**kwargs)
    
product_detail=ProductDetailView.as_view()


class ProductSearch(APIView):
     '''
     Product Search API

     Allows all users (Aunthenticated or not) to:

        Filters all available products based on:
        - category
        - Name
        - Brand
        - Price range

     Query parameters:
        ct : Category name
        n  : Product(partial match)
        b  : Brand
        p  : Approximate Price 
        
     Note:
        Price search includes ±1000 range

     '''
     queryset=models.Product.objects.all()

     def get_serializer_context(self):
        context = super().get_serializer_context()
        context['user'] = self.request.user
        return context
        
     def get(self,request):
        '''
        Filters available products using Query paramters

        Default:
            - returns all available Products
        Access:
            public 
        Response:
            200 ok -List of products
        '''
        category=self.request.GET.get('ct',None)
        name=self.request.GET.get('n',None)
        brand=self.request.GET.get('b',None)
        price=self.request.GET.get('p',None)
        queryset=self.queryset.all()

        if category:
            queryset=queryset.filter(Q(category__name__icontains=category)) 

        if name:
            queryset=queryset.filter(Q(product__name__icontains=name)) 

        if brand:
            queryset=queryset.filter(Q(brand__name__icontains=brand)) 

        if  price is not None and price.isdigit():
                value=int(price)

                #  Price search includes ±1000 range for price variance (tolerance)
                queryset=queryset|self.queryset.filter(Q(base_price=value)|Q(base_price__lte=value+1000))

        serializer=serializers.ProductSearchSerializers(queryset,many=True,context={'request':request})

        return Response(serializer.data,status=status.HTTP_200_OK)
product_search_view=ProductSearch.as_view()


class ProductImageListview(APIView):
    '''
     Product Image API

     Allows Authenticated and Verified Sellers to:
        - Upload images and videos of Products
        - AWS S3 Presigned urls are used to Upload
        
     Workflow:
      GET:
        1.Get fileName ,fileType of Media from Front-end
        2.Generate presigned urls 
        3.Return presigned url ,url of media 
      POST:
        4.save urls of media (after successful upload from front-end)

    '''
    permission_classes = [IsAuthenticated]

    queryset = models.ProductImage.objects.all()
    s3_client=boto3.client("s3",
                           aws_access_key_id = settings.AWS_ACCESS_KEY_ID,
                           aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                            region_name=settings.AWS_S3_REGION_NAME )

    def get(self,request):
        '''
        Generates pre-signed url to upload media to AWS S3

        Access:
            Authenticated
        Response:
             upload url : presigned url to upload from front-end
             ulr        : url of media (after upload)
        '''

        user=self.request.user

        # file_name for path in s3 , file_type is to seperate videos,images 
        file_name=self.request.GET.get('file_name')
        file_type=self.request.GET.get('file_type')
        
        # generate presigned urls for temporary credentials to upload media from front-end
        presigned_urls=self.s3_client.generate_presigned_url(
            'put_object',
            Params={'Bucket':settings.AWS_STORAGE_BUCKET_NAME,'Key':f'{user}/{file_type}/{file_name}'},
            ExpiresIn=3600
        )
        # its url that gets generated after successful upload from front-end
        url=f'https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonsaws.com/{user}/{file_type}/{file_name}'
        
        return Response({'upload_url':presigned_urls,'file_url':url,
                         'bucket':settings.AWS_STORAGE_BUCKET_NAME,'key':f'{user}/{file_type}/{file_name}'},
                         status=status.HTTP_200_OK)
    
    def post(self,request):
        '''
        Uploaded url's of media

        Request Body:

        Response:
            201 created     : url's are saved
            400 BAD REQUEST : validation error
        '''
        serializer=serializers.ProductImageSerializers(data=request.data,context={"request":request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data,status=status.HTTP_201_CREATED)
        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
    
productImage_retrieve_view=ProductImageListview.as_view()


class AddressView(generics.GenericAPIView):

    serializer_class = serializers.AddressSerializers

    def get_queryset(self):
        return models.Address.objects.filter(user=self.request.user)
    
    def get(self,request):
        queryset=self.get_queryset()
        serializer=self.get_serializer(queryset,many=True)
        return Response(serializer.data,status=status.HTTP_200_OK)
    
    def post(self,request):
        serializer=self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data,status=status.HTTP_201_CREATED)
    
    def patch(self,request):
        address=self.get_queryset()
        if not address:
            return Response({"error":"Address not Found"},status=404)
        serializer=self.get_serializer(data=request.data,partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data,status=status.HTTP_200_OK)

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

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['id'] = self.request.GET.get('q')
        return context
    
customer_qxns=CustomerQuestion.as_view()


class CartItem(APIView):

    permission_classes=[IsAuthenticated]
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
        product_id=self.request.get('product')
        variant_id=self.request.get('product_variant')
        quantity=int(self.request.get('quantity',1))

        if not product_id:
            return Response({"error":"product is required"},status=400)
        
        if quantity <=0:
              return Response({"error":"quantity should be positive"},status=400)

         
        cart,_=models.Cart.objects.get_or_create(user=request.user)
        
        try:
            cart_item=models.CartItem.objects.filter(
                cart=cart,
                product_id=product_id,
                product_variant_id=variant_id if variant_id else None
                )
            
            if cart_item:
                cart_item.quantity+=quantity

                if cart_item.product_variant:
                    available_stock=cart_item.product_variant.stock_qty
                else :
                    available_stock=cart_item.product.stock_qty

                if cart_item.quantity>available_stock:
                    return Response(
                        {"error":f'only {available_stock} are available'}
                    )
                cart_item.save()
                serializer=serializers.CartItemCreateSerializers(cart_item)

                return Response(
                {
                    "message": "Cart updated", 
                    "item": serializer.data
                },
                status=status.HTTP_200_OK
            )

        except models.CartItem.DoesNotExist:
                
                serializer=serializers.CartItemCreateSerializers(data=request.data,
                                                                 context={'request':request})
                
                if serializer.is_valid():
                    serializer.save()

                return Response(
                {"message": "Item added", "item":serializer.data},
                status=status.HTTP_201_CREATED)
            
        return Response(serializer.error_messages,status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self,request):

        product_id=self.request.get('product')
        variant_id=self.request.get('product_variant')
        quantity=self.request.get('quantity')

        if not product_id:
            return Response({"error":"product is required"},status=400)
        
        try:
            quantity=int(quantity)
        except(TypeError,ValueError):
            return Response(
                {'error':"invalid quantity"}
            )
        
                 
        cart=models.Cart.objects.get_object_or_404(user=request.user)

        try:
            cart_item=models.CartItem.objects.get(
                cart=cart,
                product_id=product_id,
                product_variant_id=variant_id if variant_id else None
                )
            
        except models.CartItem.DoesNotExist:
            return Response(
                {"error": "Item not found in cart"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        if quantity<0:
            cart_item.delete()
            return Response({"message": "Item removed from cart"},
                status=status.HTTP_200_OK
            )
        

        if cart_item.product_variant:
            available_stock=cart_item.product_variant.stock_qty
        else :
            available_stock=cart_item.product.stock_qty

        if cart_item.quantity>available_stock:
            return Response(
                {"error":f'only {available_stock} are available'}
            )
        
        cart_item.quantity = quantity
        cart_item.save()
        serializer=serializers.CartItemCreateSerializers(cart_item)

        return Response(
        {
            "message": "Cart updated", 
            "item": serializer.data
        },
        status=status.HTTP_200_OK
    )
    
    def delete(self, request):
     
        product_id = request.query_params.get('product')
        variant_id = request.query_params.get('variant')

        if not product_id:
            return Response(
                {"error": "Product ID is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        cart = get_object_or_404(models.Cart, user=request.user)
        
        try:
            cart_item = models.CartItem.objects.get(
                cart=cart,
                product_id=product_id,
                product_variant_id=variant_id if variant_id and variant_id != "0" else None
            )
            cart_item.delete()
            
            return Response(
                {"message": "Item removed from cart"},
                status=status.HTTP_200_OK
            )
            
        except models.CartItem.DoesNotExist:
            return Response(
                {"error": "Item not found in cart"}, 
                status=status.HTTP_404_NOT_FOUND
            )

              
cartitem=CartItem.as_view()


class ReviewView(APIView):

    permission_classes=[IsAuthenticated]
    queryset=models.Review.objects.all()

    def post(self,request):
        product_id = request.GET.get('q')  
        if not product_id:
            return Response(
                {"error": "Product id (q) is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer=serializers.ReviewSerializers(data=request.data,context={'id': product_id,'request':request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data,status=status.HTTP_201_CREATED)
        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self,request):

        product_id = request.GET.get('q')  
        if not product_id:
            return Response(
                {"error": "Product id (q) is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        review=models.Review.objects.filter(
            user=request.user,
            product_id=product_id
        ).first()

        if not review:
            return Response(
               { "error":"review does not exis"},
               status=status.HTTP_404_NOT_FOUND
            )
        else:
            serializer=serializers.ReviewSerializers(review,
                                                     data=request.data,
                                                     partial=True,
                                                     context={'id': product_id,'request':request})
            if serializer.is_valid():
               serializer.save()
               return Response(serializer.data,status=status.HTTP_201_CREATED)
        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST) 
    
    def delete(self,request):
        product_id = request.GET.get('q')  
        if not product_id:
            return Response(
                {"error": "Product id (q) is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
        count_review,_=models.Review.objects.filter(
            user=request.user,
            product_id=product_id
        ).delete()

        if count_review==0:
            return Response({"error":"review is not found"},
                            status=status.HTTP_404_NOT_FOUND)
     
        return Response({"message":"deleted successfully"},status=status.HTTP_200_OK)
    
review_list_view=ReviewView.as_view()


class BrandListCreateview(generics.ListCreateAPIView):
    queryset=models.Brand.objects.all()
    serializer_class=serializers.BrandSerializer

brand_list_create_view=BrandListCreateview.as_view()


class WhishView(APIView):
    queryset=models.Whishlist.objects.all()
    permission_classes=[IsAuthenticated]

    def get(self,request):
        queryset = self.queryset.filter(user=request.user)
        serializer=serializers.WhishlistReadSerializer(queryset,many=True,
                                                   context={"request":request})
        return Response(serializer.data,status=status.HTTP_200_OK)

    def post(self,request):
        product_id = request.GET.get('q')  
        if not product_id:
            return Response(
                {"error": "Product id (q) is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer=serializers.WhishlistCreateSerializer(data=request.data,
                                                   context={"request":request,"id":product_id})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data,status=status.HTTP_201_CREATED)
        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self,request):
        product_id = request.GET.get('q')  
        if not product_id:
            return Response(
                {"error": "Product id (q) is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        deleted_count,_=self.queryset.filter(user=self.request.user,product_id=product_id).delete()

        if deleted_count==0:
            return Response({"error":"item is not found"},
                            status=status.HTTP_404_NOT_FOUND)
    
        return Response({"message":"deleted successfully"},status=status.HTTP_200_OK)

whish_list_createview = WhishView.as_view()


class OrderView(APIView):

    def post(self,request):
         serializer=serializers.OrderSerializer(data=request.data,context={'request':request})
         if serializer.is_valid():
             serializer.save()
             return Response(serializer.data,status=status.HTTP_201_CREATED)
         return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
    
    def get(self,request):
        queryset=models.Order.objects.filter(user=self.request.user)
        serializer=serializers.OrderReadSerializers(queryset,many=True,context={"request":request})
        return Response(serializer.data,status=status.HTTP_200_OK)

order_list_create_view=OrderView.as_view()


class PaymentVIew(generics.ListCreateAPIView):
    queryset=models.Payment.objects.all()
    serializer_class=serializers.PaymentSerializers

payment_list_create_view=PaymentVIew.as_view()

    

