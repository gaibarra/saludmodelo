"""Authenticated self-service password changes; no administrator reset endpoint."""
from django.contrib.auth import get_user_model, update_session_auth_hash, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.middleware.csrf import get_token
from django.views.decorators.debug import sensitive_post_parameters
from django.utils.decorators import method_decorator
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import UserRateThrottle
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from .admin_serializers import StrictSerializer
from .models import SecurityEvent

class PasswordInput(StrictSerializer):
    current_password=serializers.CharField(max_length=256,trim_whitespace=False,write_only=True)
    new_password=serializers.CharField(max_length=128,trim_whitespace=False,write_only=True)
    confirm_password=serializers.CharField(max_length=128,trim_whitespace=False,write_only=True)

class PasswordThrottle(UserRateThrottle):
    scope='password_change'
    rate='5/min'

@method_decorator(sensitive_post_parameters('current_password','new_password','confirm_password'),name='dispatch')
class PasswordChange(APIView):
    throttle_classes=[PasswordThrottle]
    @extend_schema(request=PasswordInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request):
        form=PasswordInput(data=request.data);form.is_valid(raise_exception=True);v=form.validated_data
        user=get_user_model().objects.select_for_update().get(pk=request.user.pk)
        if not user.check_password(v['current_password']):raise ValidationError({'current_password':'La contraseña actual no es correcta.'})
        if v['new_password']!=v['confirm_password']:raise ValidationError({'confirm_password':'Las contraseñas no coinciden.'})
        if user.check_password(v['new_password']):raise ValidationError({'new_password':'Elija una contraseña distinta de la actual.'})
        try:password_validation.validate_password(v['new_password'],user=user)
        except DjangoValidationError as error:raise ValidationError({'new_password':error.messages})
        user.set_password(v['new_password']);user.save(update_fields=['password'])
        # Preserve this session; all other sessions fail Django's password hash check.
        update_session_auth_hash(request._request,user)
        SecurityEvent.objects.create(user=user,action='password.changed')
        response=Response({'detail':'Contraseña actualizada. Las demás sesiones deberán ingresar nuevamente.','csrf':get_token(request)})
        response['Cache-Control']='no-store'
        return response
