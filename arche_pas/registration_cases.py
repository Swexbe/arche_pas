# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from uuid import uuid4

from arche.interfaces import IFlashMessages
from pyramid.httpexceptions import HTTPFound

from arche_pas import _
from arche_pas.models import register_case


def callback_case_1(provider, user, data):
    provider.store(user, data)
    fm = IFlashMessages(provider.request)
    msg = _("data_tied_at_login",
            default="Since you already had an account with the same email address validated, "
                    "you've been logged in as that user. Your accounts have also been linked.")
    fm.add(msg, type="success", auto_destruct=False)
    # Will return a HTTP 302
    return provider.login(user)


def callback_case_2(provider, user, data):
    user.email_validated = True
    provider.store(user, data)
    fm = IFlashMessages(provider.request)
    msg = _("accounts_linked_verified_since_logged_in",
            default="You've linked your external login to this account.")
    fm.add(msg, type="success", auto_destruct=False)
    # Will return a HTTP 302
    return provider.login(user)


def callback_must_be_logged_in(provider, user, data):
    email = provider.get_email(data, validated=False)
    msg = _("user_email_present",
            default="There's already a user registered here with your email address: '${email}' "
                    "If this is your account, please login here first to "
                    "connect the two accounts.",
            mapping={'email': email})
    fm = IFlashMessages(provider.request)
    fm.add(msg, type='danger', auto_destruct=False, require_commit=False)
    raise HTTPFound(location=provider.request.resource_url(provider.request.root, 'login'))


def callback_register(provider, user, data):
    reg_id = str(uuid4())
    provider.request.session[reg_id] = data
    # Register this user
    return reg_id


def callback_maybe_attach_account(provider, user, data):
    """ Only for logged in users."""
    reg_id = str(uuid4())
    provider.request.session[reg_id] = data
    raise HTTPFound(location=provider.request.route_url('pas_link', provider=provider.name, reg_id=reg_id))


def includeme(config):
    """
    Different registration cases for email:
    1) Validated on server, validated locally and exist
    2) Validated on server, exists locally but not validated, user logged in
    3) Validated on server, exists locally but not validated, user not logged in
    4) Validated on server, doesn't exist locally
    4A) Validated on server, doesn't match locally but user logged in
     - change email?

    Serious security breach risk:
    5) Not validated/trusted on server, validated locally, user logged in
       - Serious risk of hack: cross site scripting or accidental attach of credentials
    6) Not validated/trusted on server, validated locally, user not logged in

    7) Not validated/trusted on server, exists locally but not validated, user logged in
    7A) Not validated/trusted on server, local user not matched, user logged in
    8) Not validated/trusted on server, exists locally but not validated, user not logged in
    9) Not validated/trusted on server, doesn't exist locally, not logged in

    10) No email from provider, user logged in
    11) No email from provider, user not logged in
    """

    register_case(
        config.registry,
        'case1',
        title = "Validated on server, validated locally and user exists",
        require_authenticated = None,
        email_validated_provider = True,
        email_validated_locally = True,
        user_exist_locally = True,
        provider_validation_trusted = True,
        callback=callback_case_1,
    )
    register_case(
        config.registry,
        'case2',
        title = "Validated on server, exists locally but not validated, user logged in",
        require_authenticated = True,
        email_validated_provider = True,
        email_validated_locally = False,
        user_exist_locally = True,
        provider_validation_trusted = True,
        callback = callback_case_2,
    )
    register_case(
        config.registry,
        'case3',
        title = "Validated on server, exists locally but not validated, user not logged in",
        require_authenticated = False,
        email_validated_provider = True,
        email_validated_locally = False,
        user_exist_locally = True,
        provider_validation_trusted = True,
        callback = callback_must_be_logged_in,
    )
    register_case(
        config.registry,
        'case4',
        title = "Validated on server, doesn't exist locally",
        require_authenticated = False,
        email_validated_provider = True,
        #email_validated_locally = False,
        user_exist_locally = False,
        provider_validation_trusted = True,
        callback = callback_register,
    )
    register_case(
        config.registry,
        'case4a',
        title = "Validated on server, doesn't match locally but is authenticated",
        require_authenticated = True,
        email_validated_provider = True,
        #email_validated_locally = False,
        user_exist_locally = False,
        provider_validation_trusted = True,
        callback = callback_maybe_attach_account,
    )
    register_case(
        config.registry,
        'case5',
        title="Not validated/trusted on server, validated locally, user logged in",
        require_authenticated = True,
        #email_validated_provider = None,
        email_validated_locally = True,
        #user_exist_locally = True, Should be caught by email_validated_locally?
        email_from_provider = None,
        provider_validation_trusted = False,
        callback = callback_maybe_attach_account,
    )
    register_case(
        config.registry,
        'case6',
        title="Not validated/trusted on server, validated locally, user not logged in",
        require_authenticated = False,
        #email_validated_provider = None,
        email_validated_locally = True,
        #user_exist_locally = True, Should be caught by email_validated_locally?
        email_from_provider = None,
        provider_validation_trusted = False,
        callback = callback_must_be_logged_in,
    )
    register_case(
        config.registry,
        'case7',
        title="Not validated/trusted on server, exists locally but not validated, user logged in",
        require_authenticated = True,
        email_validated_provider = None,
        email_validated_locally = False,
        user_exist_locally = True,
        email_from_provider = True,
        provider_validation_trusted = False,
        callback = callback_maybe_attach_account,
    )
    register_case(
        config.registry,
        'case7a',
        title="Not validated/trusted on server, local user not matched, user logged in",
        require_authenticated = True,
        email_validated_provider = None,
        email_validated_locally = False,
        user_exist_locally = False,
        email_from_provider = True,
        provider_validation_trusted = False,
        callback = callback_maybe_attach_account, #FIXME: And change email?
    )
    register_case(
        config.registry,
        'case8',
        title="Not validated/trusted on server, exists locally but not validated, user not logged in",
        require_authenticated = False,
        email_validated_provider = None,
        email_validated_locally = False,
        user_exist_locally = True,
        email_from_provider = None,
        provider_validation_trusted = False,
        callback = callback_must_be_logged_in,
    )
    register_case(
        config.registry,
        'case9',
        title="Not validated/trusted on server, doesn't exist locally",
        require_authenticated = False,
        email_validated_provider = None,
        #email_validated_locally = False,
        user_exist_locally = False,
        email_from_provider = True,
        provider_validation_trusted = False,
        callback = callback_register,
    )
    register_case(
        config.registry,
        'case10',
        title="No email from provider, user logged in",
        require_authenticated = True,
        email_validated_provider = None,
        email_validated_locally = None,
       # user_exist_locally = True,
        email_from_provider = False,
        provider_validation_trusted = None,
        callback = callback_maybe_attach_account,
    )
    register_case(
        config.registry,
        'case11',
        title="No email from provider, user not logged in",
        require_authenticated = False,
        #email_validated_provider = None,
        #email_validated_locally = None,
        #user_exist_locally = None,
        email_from_provider = False,
        #provider_validation_trusted = None,
        callback=callback_register, #Allow registration here?
    )
