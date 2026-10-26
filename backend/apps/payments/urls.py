from django.urls import path

from .views import CardPaymentView, CashPaymentView, InvoiceDetailView, InvoiceListView
from .reports import CashierSalesReportView, SalesReportView

app_name = "payments"
urlpatterns = [
    path("reports/sales/", SalesReportView.as_view(), name="sales-report"),
    path("reports/sales/own/", CashierSalesReportView.as_view(), name="cashier-sales-report"),
    path("payments/cash/", CashPaymentView.as_view(), name="cash"),
    path("payments/card/", CardPaymentView.as_view(), name="card"),
    path("invoices/", InvoiceListView.as_view(), name="invoice-list"),
    path("invoices/<int:pk>/", InvoiceDetailView.as_view(), name="invoice-detail"),
]
