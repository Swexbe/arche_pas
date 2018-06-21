# -*- coding: utf-8 -*-
import colander
import deform
from arche.interfaces import ISchemaCreatedEvent

from arche_pas import _
from arche_pas.interfaces import IPASProvider
from arche_pas.interfaces import IProviderData
from arche_pas.models import UnknownProvider


def remove_pw_option_if_pw_not_set(schema, event):
    if not event.context.password:
        if 'remove_password' in schema:
            del schema['remove_password']


@colander.deferred
def providers_to_remove_widget(node, kw):
    context = kw['context']
    request = kw['request']
    provider_data = IProviderData(context)
    values = []
    for name in provider_data:
        provider = request.registry.queryAdapter(request, IPASProvider, name=name)
        if provider:
            values.append((name, provider.title))
        else:
            up = UnknownProvider(name)
            values.append((name, up.title))
    return deform.widget.CheckboxChoiceWidget(values=values)


def confirm_validator(node, value):
    if not value:
        raise colander.Invalid(node, _("Must be checked"))


class LinkPASDataSchema(colander.Schema):
    confirm = colander.SchemaNode(
        colander.Bool(),
        title=_("Confirm"),
        validator=confirm_validator,
    )


class RemovePASDataSchema(colander.Schema):
    remove_password = colander.SchemaNode(
        colander.Bool(),
        title=_("Remove password to disable password login?"),
        description=_("remove_password_description",
                      default="You may set a new password through the 'Request password' "
                              "page when you login, in case you loose the ability to login "
                              "with other services."))
    providers_to_remove = colander.SchemaNode(
        colander.Set(),
        default=(),
        title=_("Remove authentication?"),
        description=_(
            "providers_to_remove_description",
            default="Warning: You may not login again with "
                    "any service you remove here. "
                    "However, you may tie existing accounts to a provider again, "
                    "and login that way."),
        widget=providers_to_remove_widget, )


def includeme(config):
    config.add_schema('PAS', RemovePASDataSchema, 'remove_data')
    config.add_schema('PAS', LinkPASDataSchema, 'link_data')
    config.add_subscriber(remove_pw_option_if_pw_not_set,
                          [RemovePASDataSchema, ISchemaCreatedEvent])
