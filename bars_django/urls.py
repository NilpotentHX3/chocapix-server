from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()


from rest_framework import viewsets, routers, mixins, status
from bars_api.models import *

router = routers.DefaultRouter()
for (name, x) in {
			'user': (User, UserSerializer),
			'bar': (Bar, BarSerializer),
			'account': (Account, AccountSerializer),
			'item': (Item, ItemSerializer)
		}.items():
	router.register(name,
		type("ViewSet", (viewsets.ModelViewSet,),
			{
				"queryset":x[0].objects.all(),
				"serializer_class":x[1]
			}))

router.register(r'transaction', TransactionViewSet)



urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^', include(router.urls)),
)
