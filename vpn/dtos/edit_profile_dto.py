from django import forms


class EditProfileForm(forms.Form):
    new_username = forms.CharField(max_length=150, required=True)
