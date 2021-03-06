from django.http import Http404
from django.db import models
from django.db.models import Sum, F, Prefetch, Value as V
from rest_framework import viewsets, serializers, decorators
from bars_django.utils import VirtualField, permission_logic
from rest_framework.response import Response

from bars_core.perms import RootBarRolePermissionLogic, RootBarPermissionsOrAnonReadOnly
from bars_items.models.stockitem import StockItem


@permission_logic(RootBarRolePermissionLogic())
class ItemDetails(models.Model):
    class Meta:
        app_label = 'bars_items'
    name = models.CharField(max_length=100)
    name_plural = models.CharField(max_length=100, blank=True)
    brand = models.CharField(max_length=100, blank=True)
    container = models.CharField(max_length=100, blank=True)
    container_plural = models.CharField(max_length=100, blank=True)
    unit = models.CharField(max_length=100, blank=True)
    unit_plural = models.CharField(max_length=100, blank=True)
    container_qty = models.FloatField(default=1)
    ranking_unit = models.CharField(max_length=100, blank=True)
    ranking_unit_factor = models.FloatField(default=1)

    keywords = models.CharField(max_length=200, blank=True)  # Todo: length

    def __unicode__(self):
        return self.name


class ItemDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemDetails
    _type = VirtualField("ItemDetails")

    def to_representation(self, itemdetails):
        obj = super(ItemDetailsSerializer, self).to_representation(itemdetails)

        if 'request' in self.context.keys() and self.context.get('request').method == 'GET':
            bar = self.context['request'].query_params.get('bar', None)
            if bar is not None:
                try:
                    obj["stockitem"] = itemdetails.stockitems[0].id
                except IndexError:
                    obj["stockitem"] = None
        else:
            try:
                bar = self.context['request'].bar
                stockitem = StockItem.objects.get(bar=bar, details=itemdetails)
                obj["stockitem"] = stockitem.id
            except (KeyError, StockItem.DoesNotExist):
                pass

        return obj


class ItemDetailsViewSet(viewsets.ModelViewSet):
    queryset = ItemDetails.objects.all()
    serializer_class = ItemDetailsSerializer
    permission_classes = (RootBarPermissionsOrAnonReadOnly,)
    search_fields = ('name', 'keywords')

    def list(self, request):
        bar = request.query_params.get('bar', None)
        if bar is None:
            serializer = ItemDetailsSerializer(self.filter_queryset(self.get_queryset()), many=True)
        else:
            serializer = ItemDetailsSerializer(self.filter_queryset(self.get_queryset()).prefetch_related(Prefetch('stockitem_set', queryset=StockItem.objects.filter(bar__id=bar), to_attr='stockitems')), many=True, context={'request': request})
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        bar = request.query_params.get('bar', None)
        if bar is None:
            qs = self.filter_queryset(self.get_queryset())
        else:
            qs = self.filter_queryset(self.get_queryset()).prefetch_related(Prefetch('stockitem_set', queryset=StockItem.objects.filter(bar__id=bar), to_attr='stockitems'))

        try:
            instance = qs.get(pk=pk)
        except ItemDetails.DoesNotExist:
            return Http404()

        serializer = ItemDetailsSerializer(instance, context={'request': request})
        return Response(serializer.data)

    @decorators.detail_route()
    def stats(self, request, pk):
        from bars_stats.utils import compute_transaction_stats
        f = lambda qs: qs.filter(itemoperation__target__sellitem=pk)
        aggregate = Sum(F('itemoperation__delta') * V(1)) # TODO: change if buy_unit

        stats = compute_transaction_stats(request, f, aggregate)
        return Response(stats, 200)
