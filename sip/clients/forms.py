from django import forms
from django.contrib.auth.models import User
from .models import ClientProfile
import os, subprocess
from django.conf import settings

class AddClientForm(forms.ModelForm):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)
    quota_limit = forms.CharField(help_text="e.g. 5G, 500M")

    class Meta:
        model = ClientProfile
        fields = ['storage_path', 'quota_limit']

    def save(self, commit=True):
        # 1. Create User
        username = self.cleaned_data['username']
        password = self.cleaned_data['password']
        user = User.objects.create_user(username=username, password=password)

        # 2. Create ClientProfile
        profile = super().save(commit=False)
        profile.user = user

        if commit:
            profile.save()
            # 3. Create storage folder
            os.makedirs(profile.storage_path, exist_ok=True)
            # 4. Apply Linux quota
            soft, hard = self.convert_quota_to_kb(profile.quota_limit)
            subprocess.run(['sudo', 'setquota', '-u', username,
                            str(soft), str(hard), '0', '0', settings.USER_DATA_ROOT])
        return profile

    @staticmethod
    def convert_quota_to_kb(quota_str):
        unit = quota_str[-1].upper()
        num = float(quota_str[:-1])
        if unit == 'G':
            return int(num*1024*1024), int(num*1024*1024*1.1)
        elif unit == 'M':
            return int(num*1024), int(num*1024*1.1)
        else:
            return int(num), int(num*1.1)
