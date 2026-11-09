# -*- coding: utf-8 -*-
from django.urls import path

from . import views

urlpatterns = [
    path("daily/", views.daily_report, name="inspection-daily"),
    path("weekly/", views.weekly_report, name="inspection-weekly"),
    path("export/word/", views.export_word, name="inspection-export-word"),
    path("export/excel/", views.export_excel, name="inspection-export-excel"),
]
