import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('appointments', '0001_initial'),
        ('procurement', '0001_initial'),
        ('produce', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Token',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token_number', models.CharField(db_index=True, help_text='Center sequence code e.g. LKO-001', max_length=20)),
                ('sequence_number', models.PositiveIntegerField(help_text='Daily sequential queue number per center')),
                ('date', models.DateField(default=django.utils.timezone.now)),
                ('status', models.CharField(choices=[('WAITING', 'Waiting'), ('CALLED', 'Called'), ('IN_PROGRESS', 'In Progress at Center'), ('COMPLETED', 'Completed'), ('CANCELLED', 'Cancelled')], default='WAITING', max_length=20)),
                ('counter_number', models.CharField(default='Counter 1', max_length=50)),
                ('called_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('secure_qr_uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('issued_at', models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('appointment', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='token_obj', to='appointments.appointment')),
                ('farmer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tokens', to=settings.AUTH_USER_MODEL)),
                ('procurement_center', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tokens', to='procurement.procurementcenter')),
                ('procurement_record', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='token_obj', to='procurement.procurementrecord')),
                ('produce', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tokens', to='produce.produce')),
            ],
            options={
                'ordering': ['date', 'sequence_number'],
                'unique_together': {('procurement_center', 'date', 'sequence_number')},
            },
        ),
    ]
