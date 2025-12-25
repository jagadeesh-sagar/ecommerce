from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics,status
from rest_framework.permissions import IsAuthenticated,IsAuthenticatedOrReadOnly,AllowAny
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from serializers import UserRegistrationSerializer
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator



class UserRegistrationView(generics.CreateAPIView):
    queryset =User.objects.all()
    serializer_class=UserRegistrationSerializer
    permission_classes=[AllowAny]

    def create(self,request,*args,**kwargs):

        serializer=self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user=serializer.save()
        refresh=RefreshToken.for_user(user)

        response=Response({
            'user':{
                'id':user.id,
                'username':user.username,
                'email':user.email,

            },

        },
        status=status.HTTP_201_CREATED
        )

        cookie_max_age=7*24*60*60 #seconds (7 days)
        response.set_cookie(
            key='refresh_token',
            value=str(refresh)
            httponly=True,
            secure=False ,
            samesite="Strict",
            max_age=cookie_max_age,
            expires=now()+timedata(seconds=cookie_max_age)

        )

        response.set_cookie(
            'access',
            str(refresh.access_token),
            httponly=False,
            samesite="Strict"

        )
        return response
    

class CookieTokenRefreshView(TokenRefreshView):
    serializer_class =TokenRefreshSerializer

    def post(self,request,*args,**kwargs):
        refresh_token=self.request.COOKIES.get('refresh')
        if refresh_token is None:
            return Response ({'error':'Refresh token is missing'},status=400)
        
        serializer=self.get_serializer(data={'refresh':refresh_token})
        serializer.is_valid(raise_exception=True)
        return Response({'access':serializer.validated_data['access']})



@method_decorator(ensure_csrf_cookie,name='dispatch')
class CSRFTokenView(APIView):
  
  def get(self,request,format=None):
    return Response({'csrfToken':request.Meta.get('CSRF_COOKIE')})



        

