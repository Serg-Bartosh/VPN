from django import forms


class SiteForm(forms.Form):
    url = forms.URLField(max_length=255, required=True)
    name = forms.CharField(max_length=255, required=True)
