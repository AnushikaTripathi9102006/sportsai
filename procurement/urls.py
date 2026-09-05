from django.urls import path

from . import views

app_name = "procurement"

urlpatterns = [
    path("centers/", views.centers, name="centers"),
    path("centers/details/", views.center_detail, name="center_detail"),
    path("centers/confirm/", views.confirm_center, name="confirm_center"),
    path("status/", views.status, name="status"),
    path("status/detail/", views.status_detail, name="status_detail"),

    # Officer Workflow Routes
    path("officer/appointments/", views.officer_appointments, name="officer_appointments"),
    path("officer/gate-entry/", views.officer_gate_entry, name="officer_gate_entry"),
    path("officer/gate-entry/<int:pk>/", views.officer_gate_entry, name="officer_gate_entry_action"),
    path("officer/queue/", views.officer_queue, name="officer_queue"),
    path("officer/quality-check/", views.officer_quality_check, name="officer_quality_check"),
    path("officer/quality-check/<int:pk>/", views.officer_quality_check, name="officer_quality_check_action"),
    path("officer/weighing/", views.officer_weighing, name="officer_weighing"),
    path("officer/weighing/<int:pk>/", views.officer_weighing, name="officer_weighing_action"),
    path("officer/acceptance/", views.officer_acceptance, name="officer_acceptance"),
    path("officer/acceptance/<int:pk>/", views.officer_acceptance, name="officer_acceptance_action"),
    path("officer/bills/", views.officer_bills, name="officer_bills"),
    path("officer/bills/<int:pk>/", views.officer_bills, name="officer_bills_action"),
    path("officer/payments/", views.officer_payments, name="officer_payments"),
    path("officer/payments/<int:pk>/", views.officer_payments, name="officer_payments_action"),
    path("officer/history/", views.officer_history, name="officer_history"),
]
