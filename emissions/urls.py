from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'clients', views.ClientViewSet)
router.register(r'batches', views.IngestionBatchViewSet)
router.register(r'records', views.NormalizedRecordViewSet)
router.register(r'raw-records', views.RawRecordViewSet)
router.register(r'audit-logs', views.AuditLogViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('upload/', views.upload_file, name='upload-file'),
    path('records/<int:record_id>/review/', views.review_record, name='review-record'),
    path('records/<int:record_id>/edit/', views.edit_record, name='edit-record'),
    path('records/bulk-review/', views.bulk_review, name='bulk-review'),
    path('batches/<int:batch_id>/export/', views.export_batch, name='export-batch'),
    path('batches/<int:batch_id>/summary/', views.batch_summary, name='batch-summary'),
    path('seed-units/', views.seed_units, name='seed-units'),
]
