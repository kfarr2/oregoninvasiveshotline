from django.conf import settings
from django.conf.urls import include, patterns, url
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect

from .comments import views as comments
from .notifications import views as notifications
from .perms import permissions
from .reports import views as reports
from .species import views as species
from .users import views as users
from .views import home

admin.autodiscover()

urlpatterns = patterns(
    '',
    # Examples:
    # url(r'^$', 'hotline.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    # redirects for the old site
    url(r'^reports/(?P<report_id>\d+)/?$', lambda request, report_id: redirect("reports-detail", report_id)),
    url(r'^reports/new/?$', lambda request: redirect("reports-create")),
    url(r'^home/search.*$', lambda request: redirect("reports-list")),

    # the django admin interface is always nice to have
    url(r'^admin/', include(admin.site.urls)),
    url(r'^$', home, name="home"),
    url(r'^adminpanel/?$', species.admin_panel, name='admin-panel'),
    url(r'^species/list/?$', species.list_, name='species-list'),
    url(r'^species/detail/(?P<pk>[0-9]+)/?$', permissions.is_active(species.SpeciesDetailView.as_view()), name='species-detail'),
    url(r'^species/delete/(?P<pk>[0-9]+)/?$', permissions.is_active(species.SpeciesDeleteView.as_view()), name='species-delete'),
    url(r'^species/create/?$', permissions.is_active(species.SpeciesCreateView.as_view()), name='species-create'),

    url(r'^categories/list/?$', permissions.is_staff(species.CategoryList.as_view()), name='categories-list'),
    url(r'^categories/detail/(?P<pk>[0-9]+)/?$', permissions.is_staff(species.CategoryDetailView.as_view()), name='categories-detail'),
    url(r'^categories/delete/(?P<pk>[0-9]+)/?$', permissions.is_staff(species.CategoryDeleteView.as_view()), name='categories-delete'),
    url(r'^categories/create/?$', permissions.is_staff(species.CategoryCreateView.as_view()), name='categories-create'),

    url(r'^severities/list/?$', permissions.is_staff(species.SeverityList.as_view()), name='severities-list'),
    url(r'^severities/detail/(?P<pk>[0-9]+)/?$', permissions.is_staff(species.SeverityDetailView.as_view()), name='severities-detail'),
    url(r'^severities/delete/(?P<pk>[0-9]+)/?$', permissions.is_staff(species.SeverityDeleteView.as_view()), name='severities-delete'),
    url(r'^severities/create/?$', permissions.is_staff(species.SeverityCreateView.as_view()), name='severities-create'),

    url(r'^reports/create/?$', reports.create, name='reports-create'),
    url(r'^reports/detail/(?P<report_id>\d+)/?$', reports.detail, name='reports-detail'),
    url(r'^reports/claim/(?P<report_id>\d+)/?$', reports.claim, name='reports-claim'),
    url(r'^reports/unclaim/(?P<report_id>\d+)/?$', reports.unclaim, name='reports-unclaim'),
    url(r'^reports/delete/(?P<report_id>\d+)/?$', reports.delete, name='reports-delete'),
    url(r'^reports/list/?$', reports.list_, name='reports-list'),
    url(r'^reports/help/?$', reports.help, name='reports-help'),

    url(r'^comments/edit/(?P<comment_id>\d+)/?$', comments.edit, name='comments-edit'),
    url(r'^comments/delete/(?P<comment_id>\d+)/?$', comments.delete, name='comments-delete'),

    url(r'^notifications/create/?$', notifications.create, name='notifications-create'),
    url(r'^notifications/list/?$', notifications.list_, name='notifications-list'),

    # Here we define all the URL routes for the users app. Technically, you
    # could put these routes in the app itself, but for non-reusable apps, we
    # keep them in the main urlconfs file
    url(r'^users/home/?$', users.home, name='users-home'),
    url(r'^users/detail/(?P<pk>[0-9]+)/?$', users.Detail.as_view(), name='users-detail'),
    url(r'^users/list/?$', users.list_, name='users-list'),
    url(r'^users/create/?$', users.create, name='users-create'),
    url(r'^users/edit/(?P<user_id>\d+)/?$', users.edit, name='users-edit'),
    url(r'^users/delete/(?P<user_id>\d+)/?$', users.delete, name='users-delete'),
    url(r'^users/authenticate/?$', users.authenticate, name='users-authenticate'),
    url(r'^users/avatar/(?P<user_id>\d+)/?$', users.avatar, name='users-avatar'),

    # these url routes are useful for password reset functionality and logging in and out
    # https://github.com/django/django/blob/master/django/contrib/auth/urls.py
    url(r'^login/?$', users.login, name='login'),
    url(r'', include('django.contrib.auth.urls')),

    url(r'pages/', include('hotline.pages.urls')),

    # these routes allow you to masquerade as a user, and login as them from the command line
    url(r'^cloak/', include('cloak.urls'))
)

if settings.DEBUG:  # pragma: no cover
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static("htmlcov", document_root="htmlcov", show_indexes=True)

urlpatterns += (url(r'', include('django.contrib.flatpages.urls')),)
