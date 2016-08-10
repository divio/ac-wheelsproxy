import functools

import six

from django import http
from django.forms.utils import flatatt
from django.contrib import admin
from django.contrib.admin import widgets
from django.db.models import URLField
from django.utils import html
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

from django_object_actions import (
    takes_instance_or_queryset,
    DjangoObjectActions,
)


class MethodsRequiredDecorator(object):
    def __init__(self, methods):
        self.methods = methods

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(instance, request, *args, **kwargs):
            if request.method not in self.methods:
                return http.HttpResponseBadRequest(
                    '{} not allowed'.format(request.method))
            return func(instance, request, *args, **kwargs)
        return wrapper


def require_method(method):
    return MethodsRequiredDecorator([method])


def queryset_action(func):
    return takes_instance_or_queryset(require_method('POST')(func))


def simple_code_block(code):
    return html.format_html('<pre class="simple-code-block">\n{}</pre>', code)


def admin_detail_link(instance, text=None, bold=False):
    if instance is None:
        return u'n/a'
    url = reverse('admin:{app_label}_{model_name}_change'.format(
        app_label=instance._meta.app_label,
        model_name=instance._meta.model_name,
    ), args=(instance.pk,))
    text = six.text_type(instance) if text is None else text
    style = 'font-weight: bold;' if bold else ''
    return html.format_html('<a href="{}" style="{}">{}</a>', url, style, text)


def linked_relation(attribute_name, short_description=None):
    def getter(self, obj):
        for attr in attribute_name.split('__'):
            obj = getattr(obj, attr)
        return admin_detail_link(obj)
    if short_description is None:
        short_description = attribute_name.replace('__', ' ').replace('_', ' ')
    getter.short_description = short_description
    getter.admin_order_field = attribute_name
    getter.allow_tags = True
    return getter


def linked_inline(attribute_name, short_description=None):
    def getter(self, obj):
        return admin_detail_link(obj, getattr(obj, attribute_name), bold=True)
    if short_description is None:
        short_description = attribute_name.replace('_', ' ')
    getter.short_description = short_description
    getter.admin_order_field = attribute_name
    getter.allow_tags = True
    return getter


class AdminURLFieldWidget(widgets.AdminURLFieldWidget):
    def __init__(self, attrs=None):
        final_attrs = {'class': 'vURLField'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(AdminURLFieldWidget, self).__init__(attrs=final_attrs)

    def render(self, name, value, attrs=None):
        markup = super(widgets.AdminURLFieldWidget, self).render(
            name, value, attrs)
        if value:
            value = force_text(self.format_value(value))
            final_attrs = {'href': html.smart_urlquote(value)}
            markup = html.format_html(
                '<p class="url">{}<br />{} <a{}>{}</a></p>',
                markup, _('Currently:'), flatatt(final_attrs), value,
            )
        return markup


class ModelAdmin(DjangoObjectActions, admin.ModelAdmin):
    formfield_overrides = {
        URLField: {'widget': AdminURLFieldWidget},
    }

    class Media:
        css = {
            'all': (
                'admin/css/overrides.css',
            ),
        }
