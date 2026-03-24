from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import LoginSerializer

class LoginView(APIView):

    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data['user']

            refresh = RefreshToken.for_user(user)

            return Response({
                "access": str(refresh.access_token),
                "role": user.role,
                "designation": user.designation,
                "department": user.department,
                "year": user.year,
                "section": user.section,
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)