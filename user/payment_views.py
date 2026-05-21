
from rest_framework.views import APIView
from rest_framework import generics,mixins,status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated,AllowAny,IsAdminUser
import razorpay,hashlib,json,hmac

from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.db import transaction
from django.utils import timezone

from .permissions import IsBuyer,IsSeller,IsSellerOrReadOnly,IsProductOwner,IsAdminOrReadonly
from django.db.models import Q
from . import models
from . import serializers
from . import tasks

from django.shortcuts import get_object_or_404
from django.conf import settings

from api.authentication import CookieJWTAuthentication


client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

class CashOnDeliveryView(APIView):
    permission_classes=[IsBuyer]

    def post(self,request):
        order_id=request.data.get('order_id')

        try:
            order=models.Order.objects.get(id=order_id,user=request.user)
        except models.Order.DoesNotExist:
            return Response({'error':'Order not Found'},status=400)
        
        if hasattr(order,'payment') and order.payment.status=="completed":
            return Response({'error':'Order already paid'},status=400)
        
        payment=models.Payment.objects.create(
            order=order,
            amount=order.total_amount,
            status='pending',
            payment_gateway=None,

        )

        order.status="processing"
        order.save()

        for item in order.items.select_related("product"):
            product = item.product
            product.stock_qty -= item.quantity
            product.save()

        return Response({
            'message':"Order successfully placed with cash-on-delivery",
            'order_id':order.id,
            'payment_amount':payment.amount,
            "payment_status": payment.status,
        })
        
class ConfirmCODPaymentView(APIView):
    permission_classes=[IsSeller]

    def post(self,request,order_id):
        try:
            payment=models.Payment.objects.select_related("order").get(
                order=order_id,
                payment_method='cash',
                status='pending'
            )
        except models.Payment.DoesNotExist:
            return Response({'error':"payment not found"},status=400)
        
        payment.status='completed'
        payment.created_at=timezone.now()
        payment.save()  

        payment.order.status="delivered"
        payment.order.save()

        return Response({"message": "Cash-on-Delivery payment confirmed"})


class CreateRazorpayOrderView(APIView):
    permission_classes=[IsBuyer]

    def post(self,request):
        order_id=request.data.get("order_id")

        try:
            order=models.Order.objects.get(id=order_id,user=request.user)
        except models.Order.DoesNotExist:
            return Response({"error":"Order not Found"},status=400)
        
        #check if already paid
        if hasattr(order,'payment') and order.payment.staus=='completed':
            return Response({"error":"Order already paid"},status=400)
        
        # Amount in paise as razorpay uses paise as a standard to avoid cal issues
        amount_paise=int(order.total_amount*100)

        # create order in Razorpay
        razorpay_order =client.order.create({
            "amount":amount_paise,
            "currency":"INR",
            "receipt":order.order_number, 
            "notes":{
                "order_id":str(order.id),
                "user":request.user.username,
            }
        })

        # create payment record in our DB with pending status
        payment ,created=models.Payment.objects.get_or_create(
            order=order,
            defaults={
                "amount":order.total_amount,
                "status":"pending",
                "payment_gateway":"razorpay",
                "payment_method":"online_banking", # update after verification
                "razorpay_order_id":razorpay_order["id"],
            }
        )

        if not created:
            # Update existing pending payment
            payment.razorpay_order_id=razorpay_order["id"]
            payment.status="pending"
            payment.save()

        return Response({
            "razorpay_order_id":razorpay_order['id'],
            "amount":amount_paise,
            "currency":"INR",
            "key":settings.RAZORPAY_KEY_ID,
            "order_number":order.order_number,
        })


class VerifyPaymentView(APIView):
    permission_classes = [IsBuyer]

    def post(self, request):
        razorpay_order_id = request.data.get("razorpay_order_id")
        razorpay_payment_id = request.data.get("razorpay_payment_id")
        razorpay_signature = request.data.get("razorpay_signature")

        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            return Response({"error": "Missing payment details"}, status=400)

        #verify signature
        body = f"{razorpay_order_id}|{razorpay_payment_id}"
        expected = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode(),
            body.encode(),
            hashlib.sha256
        ).hexdigest()

        if expected != razorpay_signature:
            return Response({"error": "Invalid signature"}, status=400)

        #fetch payment from Razorpay to get method details
        try:
            razorpay_payment = client.payment.fetch(razorpay_payment_id)
        except Exception:
            return Response({"error": "Could not fetch payment details"}, status=400)

        method_map = {
            "upi": "upi",
            "card": "credit_card",
            "netbanking": "online_banking",
            "wallet": "wallet",
        }
        method = method_map.get(razorpay_payment.get("method"), "online_banking")

        #update DB
        try:
            with transaction.atomic():
                payment = models.Payment.objects.select_related("order").get(
                    razorpay_order_id=razorpay_order_id,
                    order__user=request.user   # security: ensure it's their order
                )

                if payment.status == "completed":
                    return Response({
                        "message": "Payment already verified",
                        "order_number": payment.order.order_number
                    })

                payment.status = "completed"
                payment.transaction_id = razorpay_payment_id
                payment.payment_method = method
                payment.payment_date = timezone.now()
                payment.save()

                order = payment.order
                order.status = "processing"
                order.save()

                # Deduct stock
                for item in order.items.select_related("product"):
                    product = models.Product.objects.select_for_update().get(
                        id=item.product_id
                    )
                    if product.stock_qty < item.quantity:
                        raise serializers.ValidationError(
                            f"{product.name} ran out of stock"
                        )
                    product.stock_qty -= item.quantity
                    product.save()

        except models.Payment.DoesNotExist:
            return Response({"error": "Payment record not found"}, status=404)

        return Response({
            "message": "Payment successful",
            "order_number": order.order_number,
            "order_id": order.id,
            "total_amount": str(order.total_amount),
            "payment_id": razorpay_payment_id,
        })
    
# lets use this in future as it requires kyc in razorpay (but its best way to handle stuff)
@csrf_exempt
def razorpay_webhook(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    
    signature=request.headers.get('X-Razorpay-Signature')

    try:
        client.utility.verify_webhook_signature(
            request.body.decode(),
            signature,
            settings.RAZORPAY_WEBHOOK_SECRET
        )
    except Exception:
        return HttpResponse(status=400)
    
    payload=json.loads(request.body)
    event=payload.get("event")

    if event == "payment.captured":
        payment_entity=payload["payload"]["payment"]["entity"]
        razorpay_order_id=payment_entity['order_id']
        razorpay_payment_id=payment_entity['id']
        method=payment_entity.get('method','online_banking')

        method_map = {
            "upi": "upi",
            "card": "credit_card",     # refine further if needed
            "netbanking": "online_banking",
            "wallet": "wallet",
        }
    
        try:
            with transaction.atomic():
                payment=models.Payment.objects.select_related("order").get(razorpay_order_id=razorpay_order_id)
                payment.status="completed"
                payment.transaction_id=razorpay_payment_id
                payment.payment_method=method_map.get(method,"online_banking")
                payment.payment_date=timezone.now()
                payment.save()

                order=payment.order
                order.status="processing"
                order.save()

            for item in order.items.select_related("product"):
                product = models.Product.objects.select_for_update().get(id=item.product_id)
                product.stock_qty -= item.quantity
                product.save()

        except models.Payment.DoesNotExist:
            pass  # log this in production

    elif event == "payment.failed":
        razorpay_order_id = payload["payload"]["payment"]["entity"]["order_id"]
        models.Payment.objects.filter(
            razorpay_order_id=razorpay_order_id
        ).update(status="failed")

    return HttpResponse(status=200)