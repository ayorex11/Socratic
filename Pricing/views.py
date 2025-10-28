from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from .models import Pricing
from drf_yasg.utils import swagger_auto_schema
from .serializers import PricingSerializer

@api_view(['GET']) 
@permission_classes([AllowAny])
def list_pricing(request):
    """
    List all pricing plans
    """
    pricings = Pricing.objects.all()
    serializer = PricingSerializer(pricings, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_pricing(request, pk):
    """
    Retrieve specific pricing plan by ID
    """
    try:
        pricing = Pricing.objects.get(pk=pk)
        serializer = PricingSerializer(pricing)
        return Response(serializer.data)
    except Pricing.DoesNotExist:
        return Response(
            {'error': 'Pricing plan not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
@swagger_auto_schema(methods=['POST'], request_body=PricingSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_pricing(request):
    """
    Create a new pricing plan
    """
    user = request.user
    if user.is_admin == False:
        return Response(
            {'error': 'Only admins can create pricing plans'},
            status=status.HTTP_403_FORBIDDEN
        )
    serializer = PricingSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(methods=['PATCH'], request_body=PricingSerializer)
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def modify_pricing(request, pk):
    """
    Modify an existing pricing plan
    """
    user = request.user
    if user.is_admin == False:
        return Response(
            {'error': 'Only admins can modify pricing plans'},
            status=status.HTTP_403_FORBIDDEN
        )
    try:
        pricing = Pricing.objects.get(pk=pk)
    except Pricing.DoesNotExist:
        return Response(
            {'error': 'Pricing plan not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = PricingSerializer(pricing, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_pricing(request, pk):
    """
    Delete a pricing plan
    """
    user = request.user
    if user.is_admin == False:
        return Response(
            {'error': 'Only admins can delete pricing plans'},
            status=status.HTTP_403_FORBIDDEN
        )
    try:
        pricing = Pricing.objects.get(pk=pk)
        pricing.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except Pricing.DoesNotExist:
        return Response(
            {'error': 'Pricing plan not found'},
            status=status.HTTP_404_NOT_FOUND
        )