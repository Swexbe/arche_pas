from pyramid.renderers import render
from arche.portlets import PortletType

from arche_pas import get_providers
from arche_pas import _


class PASLoginPortlet(PortletType):
    name = u"pas_login"
    title = _(u"Login")

    def render(self, context, request, view, **kwargs):
        if request.authenticated_userid is None:
            adapters = [adapter for (name, adapter) in get_providers(context, request)]
            if adapters:
                response = {'portlet': self.portlet,
                            'view': view,
                            'adapters': adapters}
                return render("arche_pas:templates/login.pt", response, request = request)


def includeme(config):
    """ Add arche_pas.portlets to arche.includes in paster.ini if this portlet should be addable.
    """
    config.add_portlet(PASLoginPortlet)
