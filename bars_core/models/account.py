from django.db import models
from django.http import HttpResponseBadRequest

from rest_framework import viewsets
from rest_framework import serializers, decorators
from rest_framework.response import Response

from bars_django.utils import VirtualField, permission_logic, CurrentBarCreateOnlyDefault
from bars_core.models.bar import Bar
from bars_core.models.user import User, get_default_user
from bars_core.models.role import Role
from bars_core.perms import PerBarPermissionsOrAnonReadOnly, BarRolePermissionLogic


@permission_logic(BarRolePermissionLogic())
class Account(models.Model):
    class Meta:
        unique_together = ("bar", "owner")
        index_together = ["bar", "owner"]
        app_label = 'bars_core'
    bar = models.ForeignKey(Bar)
    owner = models.ForeignKey(User)
    money = models.FloatField(default=0)

    overdrawn_since = models.DateField(null=True)
    deleted = models.BooleanField(default=False)
    last_modified = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.owner.username + " (" + self.bar.id + ")"

    def save(self, *args, **kwargs):
        if not self.pk:
            Role.objects.get_or_create(name='customer', bar=self.bar, user=self.owner)
        super(Account, self).save(*args, **kwargs)


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        read_only_fields = ('bar', 'money', 'overdrawn_since', 'last_modified')

    _type = VirtualField("Account")
    bar = serializers.PrimaryKeyRelatedField(read_only=True, default=CurrentBarCreateOnlyDefault())


class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = (PerBarPermissionsOrAnonReadOnly,)
    filter_fields = {
        'owner': ['exact'],
        'bar': ['exact'],
        'money': ['lte', 'gte']}

    @decorators.list_route(methods=['get'])
    def me(self, request):
        bar = request.bar
        if bar is None:
            serializer = self.serializer_class(request.user.account_set.all())
        else:
            serializer = self.serializer_class(request.user.account_set.get(bar=bar))
        return Response(serializer.data)

    @decorators.detail_route()
    def stats(self, request, pk):
        from bars_stats.utils import compute_transaction_stats
        f = lambda qs: qs.filter(accountoperation__target=pk)
        aggregate = models.Sum('accountoperation__delta')

        stats = compute_transaction_stats(request, f, aggregate)
        return Response(stats, 200)

    @decorators.detail_route()
    def total_spent(self, request, pk):
        from bars_stats.utils import compute_total_spent
        f = lambda qs: qs.filter(accountoperation__target=pk)

        stats = compute_total_spent(request, f)
        return Response(stats, 200)

    @decorators.list_route(methods=['get'])
    def ranking(self, request):
        from bars_stats.utils import compute_account_ranking
        ranking = compute_account_ranking(request)
        if ranking is None:
            return HttpResponseBadRequest("I can only give a ranking within a bar")
        else:
            return Response(ranking, 200)


# default_account_map = {}
def get_default_account(bar):
    # global default_account_map
    user = get_default_user()
    # if bar.id not in default_account_map:
    #     default_account_map[bar.id], _ = Account.objects.get_or_create(owner=user, bar=bar)
    x, _ = Account.objects.get_or_create(owner=user, bar=bar)
    return x
