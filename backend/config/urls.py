from core.report_schedules import ReportScheduleHistory
from core.exceptional_mfa import RecoveryRequests,RecoveryReview
from core.tracking.views import AdministrativeTimeRequest,AdministrativeTimeDecision,AdministrativeTimeList
from core.source_changes import SourceChanges,SourceReview
from core.reservations import PlanningControl
from core.task_capacity import TaskCapacity
from django.urls import path,include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView,SpectacularSwaggerView
from core.views import *
from core.interviews import InterviewView
from core.mfa import MFAView
from core.tracking.views import Board,TaskDetail,TaskChange,BaselineDecision,BaselinePreview,DependencyOptions,TaskHistory,TaskState,TaskTime,TaskTimeCorrection,Calendar,SourceCalendar
from core.compliance import ComplianceOptions,ComplianceList,ComplianceDetail,ComplianceCheck,ComplianceApprove,ComplianceExport
from core.capacity import Institutions,CapacityBoard,CapacityReview
from core.decisions import DecisionList,DecisionDetail
from core.reports import WeeklyReport
from core.report_delivery import ReportDistribution, ReportInbox, ReportAcknowledge
from core.report_schedules import ReportScheduleView, ReportBackfillView
from core.decision_notices import DecisionNoticeAcknowledge
from core.saved_reports import SavedReportList, SavedReportDetail, ReportDispositionView
from core.ai.views import AnswerReleaseView,AnswerReleaseRevokeView,DecisionView,PolicyView,ReleaseView,ReleaseRevokeView,AssistantView,ResultView
from core.document_views import DocumentView,FragmentView,RetryView
from core.consultation_views import ConsultationView
from core.admin_views import SetupView,CampusCreate,SiteCreate,UserCreate,ServiceAdminView,AssignmentView,CatalogView,QuestionnaireView
r=DefaultRouter();r.register('services',ServiceView,basename='service');r.register('answers',AnswerView,basename='answer');r.register('tasks',TaskView,basename='task')
r.register('administration/services',ServiceAdminView,basename='admin-service')
r.register('administration/assignments',AssignmentView,basename='assignment')
r.register('questionnaires',QuestionnaireView,basename='questionnaire')
r.register('consultations',ConsultationView,basename='consultation')
urlpatterns=[path('api/v1/reports/services/<int:service>/schedule/runs/',ReportScheduleHistory.as_view()),path('api/v1/security/recoveries/',RecoveryRequests.as_view()),path('api/v1/security/recoveries/<int:pk>/review/',RecoveryReview.as_view()),path('api/v1/tracking/time/<int:pk>/administrative/',AdministrativeTimeRequest.as_view()),path('api/v1/tracking/time-requests/<int:pk>/decision/',AdministrativeTimeDecision.as_view()),path('api/v1/tracking/tasks/<int:pk>/time-requests/',AdministrativeTimeList.as_view()),path('api/v1/questionnaires/<int:pk>/source-changes/',SourceChanges.as_view()),path('api/v1/source-changes/<int:pk>/review/',SourceReview.as_view()),path('api/v1/tracking/tasks/<int:pk>/history/',TaskHistory.as_view()),path('api/v1/tracking/services/<int:service>/dependencies/',DependencyOptions.as_view()),path('api/v1/tracking/changes/<int:pk>/preview/',BaselinePreview.as_view()),path('api/v1/capacity/institutions/<int:institution>/planning/',PlanningControl.as_view()),path('api/v1/tracking/services/<int:service>/capacity/',TaskCapacity.as_view()),path('api/v1/tracking/time/<int:pk>/correct/',TaskTimeCorrection.as_view()),path('api/v1/reports/inbox/',ReportInbox.as_view()),path('api/v1/reports/deliveries/<int:pk>/acknowledge/',ReportAcknowledge.as_view()),path('api/v1/reports/saved/<int:pk>/distribution/',ReportDistribution.as_view()),path('api/v1/reports/services/<int:service>/backfill/',ReportBackfillView.as_view()),path('api/v1/reports/services/<int:service>/schedule/',ReportScheduleView.as_view()),path('api/v1/decisions/<int:pk>/acknowledge/',DecisionNoticeAcknowledge.as_view()),path('api/v1/reports/saved/<int:pk>/disposition/',ReportDispositionView.as_view()),path('api/v1/reports/services/<int:service>/saved/',SavedReportList.as_view()),path('api/v1/reports/saved/<int:pk>/',SavedReportDetail.as_view()),path('api/v1/capacity/institutions/',Institutions.as_view()),path('api/v1/capacity/institutions/<int:institution>/',CapacityBoard.as_view()),path('api/v1/capacity/changes/<int:pk>/review/',CapacityReview.as_view()),path('api/v1/decisions/services/<int:service>/',DecisionList.as_view()),path('api/v1/decisions/<int:pk>/',DecisionDetail.as_view()),path('api/v1/reports/services/<int:service>/weekly/',WeeklyReport.as_view()),path('api/v1/reports/services/<int:service>/weekly/export/',WeeklyReport.as_view(),{'export':True}),path('api/v1/ai/answer-releases/<int:instance>/',AnswerReleaseView.as_view()),path('api/v1/ai/answer-releases/<int:pk>/revoke/',AnswerReleaseRevokeView.as_view()),path('api/v1/interviews/<int:instance>/',InterviewView.as_view()),path('api/v1/mfa/',MFAView.as_view()),path('api/v1/tracking/services/<int:service>/',Board.as_view()),path('api/v1/tracking/services/<int:service>/calendar/',Calendar.as_view()),path('api/v1/tracking/services/<int:service>/source/',SourceCalendar.as_view()),path('api/v1/tracking/tasks/<int:pk>/',TaskDetail.as_view()),path('api/v1/tracking/tasks/<int:pk>/change/',TaskChange.as_view()),path('api/v1/tracking/tasks/<int:pk>/state/',TaskState.as_view()),path('api/v1/tracking/tasks/<int:pk>/time/',TaskTime.as_view()),path('api/v1/tracking/changes/<int:pk>/decision/',BaselineDecision.as_view()),path('api/v1/compliance/services/<int:service>/options/',ComplianceOptions.as_view()),path('api/v1/compliance/services/<int:service>/export/',ComplianceExport.as_view()),path('api/v1/compliance/services/<int:service>/',ComplianceList.as_view()),path('api/v1/compliance/records/<int:pk>/',ComplianceDetail.as_view()),path('api/v1/compliance/records/<int:pk>/test/',ComplianceCheck.as_view()),path('api/v1/compliance/records/<int:pk>/review/',ComplianceApprove.as_view()),path('api/v1/ai/requests/<int:pk>/decision/',DecisionView.as_view()),path('api/v1/ai/policies/<int:service>/',PolicyView.as_view()),path('api/v1/ai/releases/<int:instance>/',ReleaseView.as_view()),path('api/v1/ai/releases/<int:pk>/revoke/',ReleaseRevokeView.as_view()),path('api/v1/ai/questions/<int:instance>/',AssistantView.as_view()),path('api/v1/ai/requests/<int:pk>/',ResultView.as_view()),path('api/v1/evidence/<uuid:pk>/retry/',RetryView.as_view()),path('api/v1/evidence/<uuid:pk>/',DocumentView.as_view()),path('api/v1/evidence/<uuid:pk>/fragments/',FragmentView.as_view()),path('api/v1/administration/setup/',SetupView.as_view()),path('api/v1/administration/campuses/',CampusCreate.as_view()),path('api/v1/administration/sites/',SiteCreate.as_view()),path('api/v1/administration/users/',UserCreate.as_view()),path('api/v1/administration/catalog/',CatalogView.as_view()),path('api/v1/session/',SessionView.as_view()),path('api/v1/dashboard/',DashboardView.as_view()),path('api/v1/evidence/<uuid:pk>/download/',DownloadView.as_view()),path('api/v1/',include(r.urls)),path('api/v1/schema/',SpectacularAPIView.as_view(),name='schema'),path('api/v1/docs/',SpectacularSwaggerView.as_view(url_name='schema'))]

from core.public_portal import PublicServices,PatientRegister,PatientSession,PatientAppointments,PatientAppointmentDetail,StaffAppointments,StaffAppointmentDecision
urlpatterns += [
    path('api/v1/public/services/',PublicServices.as_view()),
    path('api/v1/public/register/',PatientRegister.as_view()),
    path('api/v1/public/session/',PatientSession.as_view()),
    path('api/v1/public/appointments/',PatientAppointments.as_view()),
    path('api/v1/public/appointments/<uuid:public_id>/withdraw/',PatientAppointmentDetail.as_view()),
    path('api/v1/staff/appointments/',StaffAppointments.as_view()),
    path('api/v1/staff/appointments/<uuid:public_id>/decision/',StaffAppointmentDecision.as_view()),
]

from core.academic import AcademicOptions,AcademicCycles,AcademicStudents,AcademicPlacements,AcademicPlacementRevoke,AcademicPractices,AcademicResubmit,AcademicReview,AcademicHistory,AcademicSummary
urlpatterns += [
    path('api/v1/academic/options/',AcademicOptions.as_view()),
    path('api/v1/academic/cycles/',AcademicCycles.as_view()),
    path('api/v1/academic/students/',AcademicStudents.as_view()),
    path('api/v1/academic/placements/',AcademicPlacements.as_view()),
    path('api/v1/academic/placements/<int:pk>/revoke/',AcademicPlacementRevoke.as_view()),
    path('api/v1/academic/practices/',AcademicPractices.as_view()),
    path('api/v1/academic/practices/<int:pk>/resubmit/',AcademicResubmit.as_view()),
    path('api/v1/academic/practices/<int:pk>/review/',AcademicReview.as_view()),
    path('api/v1/academic/practices/<int:pk>/history/',AcademicHistory.as_view()),
    path('api/v1/academic/summary/',AcademicSummary.as_view()),
]

from core.academic_assessment import AcademicRubrics,AcademicEvaluations,AcademicEvaluationHistory,AcademicReports,AcademicReportDetail,AcademicReportClose,AcademicCycleReopen
urlpatterns += [
    path('api/v1/academic/rubrics/',AcademicRubrics.as_view()),
    path('api/v1/academic/placements/<int:placement>/evaluations/',AcademicEvaluations.as_view()),
    path('api/v1/academic/placements/<int:placement>/evaluations/history/',AcademicEvaluationHistory.as_view()),
    path('api/v1/academic/cycles/<int:cycle>/reports/',AcademicReports.as_view()),
    path('api/v1/academic/reports/<int:pk>/',AcademicReportDetail.as_view()),
    path('api/v1/academic/reports/<int:pk>/close/',AcademicReportClose.as_view()),
    path('api/v1/academic/cycles/<int:cycle>/reopen/',AcademicCycleReopen.as_view()),
]

from core.school_views import Schools,SchoolDashboard,SchoolManagement,SchoolUserCreate,SchoolServiceCreate,SchoolGrants,SchoolGrantRevoke
urlpatterns += [
    path('api/v1/schools/',Schools.as_view()),
    path('api/v1/schools/<int:pk>/',SchoolDashboard.as_view()),
    path('api/v1/schools/<int:pk>/management/',SchoolManagement.as_view()),
    path('api/v1/schools/<int:pk>/users/',SchoolUserCreate.as_view()),
    path('api/v1/schools/<int:pk>/services/',SchoolServiceCreate.as_view()),
    path('api/v1/schools/<int:pk>/academic-grants/',SchoolGrants.as_view()),
    path('api/v1/schools/<int:pk>/academic-grants/<int:grant>/revoke/',SchoolGrantRevoke.as_view()),
]

from core.school_users import SchoolAccounts,SchoolAccountDetail,SchoolAccountReactivate
urlpatterns += [
    path('api/v1/schools/<int:pk>/accounts/',SchoolAccounts.as_view()),
    path('api/v1/schools/<int:pk>/accounts/<int:user>/',SchoolAccountDetail.as_view()),
    path('api/v1/schools/<int:pk>/accounts/<int:user>/reactivate/',SchoolAccountReactivate.as_view()),
]

from core.cash import CashServices,CashCandidates,CashShifts,CashDetail,CashMovements,CashSummary
urlpatterns += [
    path('api/v1/cash/services/',CashServices.as_view()),
    path('api/v1/cash/services/<int:pk>/responsibles/',CashCandidates.as_view()),
    path('api/v1/cash/shifts/',CashShifts.as_view()),
    path('api/v1/cash/shifts/<int:pk>/',CashDetail.as_view()),
    path('api/v1/cash/shifts/<int:pk>/movements/',CashMovements.as_view()),
    path('api/v1/cash/summary/',CashSummary.as_view()),
]

from core.school_users import SchoolAccountName
urlpatterns += [path("api/v1/schools/<int:pk>/accounts/<int:user>/name/",SchoolAccountName.as_view())]
