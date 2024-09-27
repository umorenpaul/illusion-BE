from django.shortcuts import render
from accounts.serializers import ProfileSerializer
from permissions import permissions
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

# Create your views here.
from .models import *
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from serializers.serializers import *
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from datetime import timedelta
from rest_framework.exceptions import PermissionDenied
import uuid
import jwt
from django.conf import settings
import datetime
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model, authenticate, login




class UserRegistrationView(APIView):
    """
    API view to handle the registration of a new user.
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='First Name'),
                'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Last Name'),
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='Password'),
                'confirm_password': openapi.Schema(type=openapi.TYPE_STRING, description='Confirm Password'),
                'company': openapi.Schema(type=openapi.TYPE_STRING, description='Company'),
                'role': openapi.Schema(type=openapi.TYPE_STRING, enum=['Employee', 'Employer'], description='Role'),
            },
            required=['first_name', 'last_name', 'email', 'password', 'confirm_password', 'role'],
        ),
        responses={201: 'Account Created', 400: 'Error'}
    )
    def post(self, request):
        data = request.data

        # Check if password and confirm password match
        if data['password'] != data.get('confirm_password'):
            return Response({'error': 'Passwords do not match'}, status=status.HTTP_400_BAD_REQUEST)

        # Serialize the data for user creation
        serializer = UserSerializer(data={
            'first_name': data['first_name'],
            'last_name': data['last_name'],
            'email': data['email'],
            'password': data['password'],
            'company': data.get('company', ''),
            'role': data['role']
        })

        # Validate and save user
        if serializer.is_valid():
            user = serializer.save()

            # Generate tokens for the user
            response_data = {
                'access_token': str(AccessToken.for_user(user)),
                'refresh_token': str(RefreshToken.for_user(user)),
                'message': 'Account Creation Successful'
            }

            return Response(response_data, status=status.HTTP_201_CREATED)
        
        # Return errors if any
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='Password'),
            },
            required=['email', 'password'],
        ),
        responses={200: 'Token', 400: 'Error'}
    )
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response({'error': 'Email and password are required'}, status=status.HTTP_400_BAD_REQUEST)

        # Use Django's built-in authenticate function
        user = authenticate(request, username=email, password=password)

        if user is None:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        # Generate tokens and return response data
        response_data = {
            'access_token': str(AccessToken.for_user(user)),
            'refresh_token': str(RefreshToken.for_user(user)),
            'user_id': user.id,
            'email': user.email,
            'role': user.role,
        }

        return Response(response_data, status=status.HTTP_200_OK)


class GoogleSignUpView(APIView):
    def post(self, request):
        serializer = GoogleSignUpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        # Generate JWT token
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_200_OK)



class ProtectedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"message": "You are authenticated"}, status=200)
    

class ProfileView(APIView):
    serializer_class = ProfileSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        return User.objects.filter(user=self.kwargs['id'])

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
    

class UserViewSet(APIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [APIView]

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return super().get_permissions()