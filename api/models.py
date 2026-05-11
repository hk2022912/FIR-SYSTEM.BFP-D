from django.db import models
from django.contrib.auth.models import User


class Incident(models.Model):
    dt       = models.CharField(max_length=100)
    loc      = models.TextField()
    inv      = models.CharField(max_length=30)
    occ      = models.CharField(max_length=200)
    dmg_raw  = models.BigIntegerField(default=0)
    alarm    = models.CharField(max_length=20)
    sta      = models.CharField(max_length=100)
    eng      = models.CharField(max_length=100)
    by_user  = models.CharField(max_length=200)
    inj_c    = models.IntegerField(default=0)
    inj_b    = models.IntegerField(default=0)
    cas_c    = models.IntegerField(default=0)
    cas_b    = models.IntegerField(default=0)
    rem      = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='incidents'
    )

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"[{self.id}] {self.dt} — {self.loc}"


class OTPRequest(models.Model):
    email      = models.EmailField()
    otp        = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used    = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"OTP for {self.email} ({'used' if self.is_used else 'active'})"