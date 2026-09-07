from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('message', models.TextField()),
                ('notification_type', models.CharField(choices=[('GENERAL', 'General Notification'), ('PRODUCE', 'Produce Registration / Update'), ('PROCUREMENT', 'Procurement Request / Status'), ('APPOINTMENT', 'Appointment Schedule'), ('TOKEN', 'Token & Live Queue'), ('QUALITY', 'Quality Inspection'), ('WEIGHING', 'Scale Weighing'), ('BILL', 'Procurement Bill'), ('PAYMENT', 'Payment & Payout'), ('SYSTEM', 'System Alert / Approval')], default='GENERAL', max_length=50)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('read_at', models.DateTimeField(blank=True, null=True)),
                ('target_url', models.CharField(blank=True, default='', max_length=255)),
                ('related_object_type', models.CharField(blank=True, default='', max_length=50)),
                ('related_object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('event_key', models.CharField(blank=True, db_index=True, default='', max_length=100)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
