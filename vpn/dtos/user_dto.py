from django import forms


class FormUser(forms.Form):
    username = forms.CharField(max_length=150, required=True)
    password = forms.CharField(max_length=50, required=True)
    email = forms.EmailField(max_length=250, required=True)
