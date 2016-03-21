from django.contrib import admin
from django.utils import html
from django.core.urlresolvers import reverse
from django.template.defaultfilters import filesizeformat

from . import models


def admin_detail_url(instance, text=None):
    if instance._meta.proxy_for_model:
        model_name = instance._meta.proxy_for_model._meta.model_name
    else:
        model_name = instance._meta.model_name
    url = reverse('admin:{app_label}_{model_name}_change'.format(
        app_label=instance._meta.app_label,
        model_name=model_name,
    ), args=(instance.id,))
    text = unicode(instance) if text is None else text
    return html.format_html('<a href="{}">{}</a>', url, text)


class PlatformAdmin(admin.ModelAdmin):
    pass

admin.site.register(models.Platform, PlatformAdmin)


class BackingIndexAdmin(admin.ModelAdmin):
    list_display = ('slug', 'url')

    readonly_fields = (
        'formatted_last_upstream_serial',
    )

    def formatted_last_upstream_serial(self, instance):
        upstream_serial = instance.last_upstream_serial()
        return '{} ({} events to sync)'.format(
            upstream_serial,
            upstream_serial - instance.last_update_serial,
        )
    formatted_last_upstream_serial.short_description = 'last upstream serial'

admin.site.register(models.BackingIndex, BackingIndexAdmin)


class ReleaseInline(admin.TabularInline):
    fields = (
        'admin_link',
    )
    readonly_fields = (
        'admin_link',
    )
    model = models.Release
    extra = 0

    def admin_link(self, instance):
        return admin_detail_url(instance, instance.version)


class PackageAdmin(admin.ModelAdmin):
    list_display = ('slug', 'index')
    search_fields = ('name',)
    list_filter = (
        'index',
    )
    inlines = (
        ReleaseInline,
    )

admin.site.register(models.Package, PackageAdmin)


class BuildInline(admin.TabularInline):
    fields = (
        'admin_link',
        'is_built',
        'formatted_filesize',
    )
    readonly_fields = (
        'admin_link',
        'is_built',
        'formatted_filesize',
    )
    model = models.Build
    extra = 0

    def admin_link(self, instance):
        return admin_detail_url(instance, instance.platform.slug)
    admin_link.short_description = 'platform'

    def formatted_filesize(self, instance):
        if instance.is_built():
            return filesizeformat(instance.filesize)
        else:
            return 'n/d'
    formatted_filesize.short_description = 'wheel size'


class ReleaseAdmin(admin.ModelAdmin):
    raw_id_fields = (
        'package',
    )
    search_fields = ['package__name']
    inlines = (
        BuildInline,
    )

admin.site.register(models.Release, ReleaseAdmin)


class BuildStatusListFilter(admin.SimpleListFilter):
    title = 'build status'
    parameter_name = 'is_built'

    def lookups(self, request, model_admin):
        return (
            ('no', 'Not yet built'),
            ('yes', 'Already built'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'no':
            return queryset.filter(build='')
        if self.value() == 'yes':
            return queryset.exclude(build='')


class BuildAdmin(admin.ModelAdmin):
    list_display = (
        'package_name',
        'version',
        'platform_name',
        'is_built',
    )

    list_filter = (
        'platform',
        'release__package__index',
        BuildStatusListFilter,
    )

    readonly_fields = (
        'formatted_requirements',
    )

    search_fields = ['release__package__name']

    raw_id_fields = (
        'release',
    )

    def platform_name(self, build):
        return build.platform.slug

    def package_name(self, build):
        return build.release.package.name

    def version(self, build):
        return build.release.version

    def is_built(self, build):
        return bool(build.build)
    is_built.boolean = True

    def formatted_requirements(self, instance):
        reqs = instance.requirements
        if reqs is not None:
            return '\n'.join(str(r) for r in reqs) if reqs else 'No dependencies'
        else:
            return 'n/d'
    formatted_requirements.short_description = 'requirements'

admin.site.register(models.Build, BuildAdmin)
