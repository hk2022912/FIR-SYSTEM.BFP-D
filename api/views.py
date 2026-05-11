import random
import string
from datetime import timedelta

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Incident, OTPRequest
from .serializers import IncidentSerializer


def _make_otp():
    return ''.join(random.choices(string.digits, k=6))


# ── LOGIN ──────────────────────────────────────────────────────────────────

@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '')

    if not username or not password:
        return Response({'message': 'Username and password are required.'}, status=400)

    user = authenticate(username=username, password=password)
    if not user:
        return Response({'message': 'Incorrect username or password.'}, status=401)

    token, _ = Token.objects.get_or_create(user=user)
    display  = user.get_full_name() or user.username
    return Response({'token': token.key, 'display': display})


# ── LOGOUT ─────────────────────────────────────────────────────────────────

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        request.user.auth_token.delete()
    except Exception:
        pass
    return Response({'message': 'Logged out.'})


# ── INCIDENTS LIST / CREATE ────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def incident_list(request):
    if request.method == 'GET':
        qs = Incident.objects.all()
        return Response(IncidentSerializer(qs, many=True).data)

    serializer = IncidentSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(created_by=request.user)
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)


# ── INCIDENT DETAIL / UPDATE / DELETE ─────────────────────────────────────

@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def incident_detail(request, pk):
    try:
        incident = Incident.objects.get(pk=pk)
    except Incident.DoesNotExist:
        return Response({'message': 'Not found.'}, status=404)

    if request.method == 'GET':
        return Response(IncidentSerializer(incident).data)

    if request.method in ('PUT', 'PATCH'):
        serializer = IncidentSerializer(incident, data=request.data, partial=(request.method == 'PATCH'))
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    incident.delete()
    return Response(status=204)


# ── BULK IMPORT ────────────────────────────────────────────────────────────

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def incident_bulk(request):
    records = request.data.get('records', [])
    if not isinstance(records, list) or not records:
        return Response({'message': 'Provide a non-empty records list.'}, status=400)

    imported, errors = 0, []

    for idx, rec in enumerate(records):
        data = {
            'dt':      rec.get('dt', ''),
            'loc':     rec.get('loc', ''),
            'inv':     rec.get('inv', ''),
            'occ':     rec.get('occ', ''),
            'dmg_raw': rec.get('dmgRaw', rec.get('dmg_raw', 0)),
            'alarm':   rec.get('alarm', ''),
            'sta':     rec.get('sta', ''),
            'eng':     rec.get('eng', ''),
            'by_user': rec.get('by', rec.get('by_user', '')),
            'inj_c':   rec.get('injC', rec.get('inj_c', 0)),
            'inj_b':   rec.get('injB', rec.get('inj_b', 0)),
            'cas_c':   rec.get('casC', rec.get('cas_c', 0)),
            'cas_b':   rec.get('casB', rec.get('cas_b', 0)),
            'rem':     rec.get('rem', ''),
        }
        s = IncidentSerializer(data=data)
        if s.is_valid():
            s.save(created_by=request.user)
            imported += 1
        else:
            errors.append({'row': idx + 1, 'errors': s.errors})

    return Response({'imported': imported, 'errors': errors}, status=201)


# ── FORGOT PASSWORD — STEP 1: send OTP ────────────────────────────────────

@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def forgot_password(request):
    email = request.data.get('email', '').strip().lower()
    if not email:
        return Response({'message': 'Email is required.'}, status=400)

    user = User.objects.filter(email__iexact=email).first()
    if not user:
        return Response({'message': 'If that email is registered, a code has been sent.'})

    OTPRequest.objects.filter(email__iexact=email, is_used=False).update(is_used=True)

    code = _make_otp()
    OTPRequest.objects.create(email=email, otp=code)

    try:
        send_mail(
            subject='FIRS — Your Password Reset Code',
            message=(
                f'Hello {user.get_full_name() or user.username},\n\n'
                f'Your 6-digit verification code is: {code}\n\n'
                f'It expires in {settings.OTP_EXPIRY_MINUTES} minutes.\n'
                f'If you did not request this, ignore this message.\n\n'
                f'— Bureau of Fire Protection, Cagayan de Oro City'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception as e:
        return Response({'message': f'Could not send email: {e}'}, status=500)

    return Response({'message': 'Verification code sent. Check your email.'})


# ── FORGOT PASSWORD — STEP 2: verify OTP ──────────────────────────────────

@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def verify_otp(request):
    email = request.data.get('email', '').strip().lower()
    code  = request.data.get('otp', '').strip()

    if not email or not code:
        return Response({'message': 'Email and OTP are required.'}, status=400)

    cutoff = timezone.now() - timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
    record = OTPRequest.objects.filter(
        email__iexact=email,
        otp=code,
        is_used=False,
        created_at__gte=cutoff,
    ).order_by('-created_at').first()

    if not record:
        return Response({'message': 'Invalid or expired code.'}, status=400)

    return Response({'message': 'Code verified.'})


# ── FORGOT PASSWORD — STEP 3: reset password ──────────────────────────────

@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def reset_password(request):
    email   = request.data.get('email', '').strip().lower()
    code    = request.data.get('otp', '').strip()
    new_pw  = request.data.get('new_password', '')
    confirm = request.data.get('confirm_password', '')

    if not all([email, code, new_pw, confirm]):
        return Response({'message': 'All fields are required.'}, status=400)
    if new_pw != confirm:
        return Response({'message': 'Passwords do not match.'}, status=400)
    if len(new_pw) < 8:
        return Response({'message': 'Password must be at least 8 characters.'}, status=400)

    cutoff = timezone.now() - timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
    record = OTPRequest.objects.filter(
        email__iexact=email,
        otp=code,
        is_used=False,
        created_at__gte=cutoff,
    ).order_by('-created_at').first()

    if not record:
        return Response({'message': 'Invalid or expired code.'}, status=400)

    user = User.objects.filter(email__iexact=email).first()
    if not user:
        return Response({'message': 'No account found for that email.'}, status=404)

    user.set_password(new_pw)
    user.save()

    record.is_used = True
    record.save()

    Token.objects.filter(user=user).delete()

    return Response({'message': 'Password updated. Please log in.'})