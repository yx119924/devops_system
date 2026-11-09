# -*- coding: utf-8 -*-
from django.urls import path

from . import views

urlpatterns = [
    path("daily/", views.daily_report, name="inspection-daily"),
    path("weekly/", views.weekly_report, name="inspection-weekly"),
    path("export/word/", views.export_word, name="inspection-export-word"),
    path("export/excel/", views.export_excel, name="inspection-export-excel"),
    path("export/weekly/word/", views.export_weekly_word, name="inspection-export-weekly-word"),
    path("export/weekly/excel/", views.export_weekly_excel, name="inspection-export-weekly-excel"),
]
