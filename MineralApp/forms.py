from django import forms
from .models import ArticuloPanol, ArticuloBodega

#Formulario para subir archivos
class UploadFileForm(forms.Form):
    file = forms.FileField(label='Selecciona un archivo')

#Formulario de Articulo en Bodega
class ArticuloBodegaForm(forms.ModelForm):
    class Meta:
        model = ArticuloBodega
        fields = ['nombre_articulo', 'descripcion_articulo', 'cantidad', 'bodega']

class ArticuloPanolForm(forms.ModelForm):
    class Meta:
        model = ArticuloPanol
        fields = ['nombre_articulo', 'descripcion_articulo', 'cantidad', 'panol']