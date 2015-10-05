from django.contrib import admin
from . import models


class PlatformAdmin(admin.ModelAdmin):
    pass

admin.site.register(models.Platform, PlatformAdmin)


class BackingIndexAdmin(admin.ModelAdmin):
    list_display = ('slug', 'url')

admin.site.register(models.BackingIndex, BackingIndexAdmin)


class PackageAdmin(admin.ModelAdmin):
    list_display = ('slug',)

admin.site.register(models.Package, PackageAdmin)


class ReleaseAdmin(admin.ModelAdmin):
    raw_id_fields = (
        'package',
    )

admin.site.register(models.Release, ReleaseAdmin)


class BuildAdmin(admin.ModelAdmin):
    list_display = (
        'package_name',
        'version',
        'platform_name',
        'is_built',
    )

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

admin.site.register(models.Build, BuildAdmin)
