from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/switch-user/(?P<username>.+)', 'hive.admin_utils.switch_user',
        name='switch_user'),
    url(r'^admin/switch-user-back', 'hive.admin_utils.switch_user_back',
        name='switch_user_back'),
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^accounts/', include('hive.account_urls')),
    url(r'^minigroup_digestif/', include('minigroup_digestif.urls')),
    url(r'', include('directory.urls')),
)
