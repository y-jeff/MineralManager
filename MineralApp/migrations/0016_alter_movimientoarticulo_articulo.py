# Generated by Django 5.1.4 on 2024-12-08 16:57

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('MineralApp', '0015_alter_movimientoarticulo_articulo_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='movimientoarticulo',
            name='articulo',
            field=models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='MineralApp.articulobodega'),
        ),
    ]
