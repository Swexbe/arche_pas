import colander
from arche.schemas import FinishRegistrationSchema
from arche.schemas import RegistrationSchema
from arche.interfaces import ISchemaCreatedEvent


@colander.deferred
def deferred_token_default(node, kw):
    request = kw['request']
    return request.params['token']


class PASRegisterForm(FinishRegistrationSchema, RegistrationSchema):
    pass


def remove_pw_form(schema, event):
    if 'password' in schema:
        del schema['password']


def includeme(config):
    config.add_content_schema('Auth', PASRegisterForm, 'pas_register')
    config.add_subscriber(remove_pw_form, [PASRegisterForm, ISchemaCreatedEvent])
