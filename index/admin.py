from django.contrib import admin
from . import models


class BackingIndexAdmin(admin.ModelAdmin):
    list_display = ('slug', 'url')

admin.site.register(models.BackingIndex, BackingIndexAdmin)


class PackageAdmin(admin.ModelAdmin):
    pass

admin.site.register(models.Package)


admin.site.register(models.Release)


admin.site.register(models.Platform)


class BuildAdmin(admin.ModelAdmin):
    list_display = (
        'package_name',
        'version',
        'platform_name',
    )

    def platform_name(self, build):
        return build.platform.slug

    def package_name(self, build):
        return build.release.package.slug

    def version(self, build):
        return build.release.version

admin.site.register(models.Build, BuildAdmin)
