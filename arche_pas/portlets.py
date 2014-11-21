from pyramid.renderers import render
from arche.portlets import PortletType

from triart_site import _
from arche_pas.interfaces import IPluggableAuth


class PASLoginPortlet(PortletType):
    name = u"pas_login"
    title = _(u"Login")

    def render(self, context, request, view, **kwargs):
        if request.authenticated_userid is None:
            #import pdb;pdb.set_trace()
            adapters = [adapter for (name, adapter) in request.registry.getAdapters([view.root, request], IPluggableAuth)]
            print adapters
            if adapters:
                response = {'portlet': self.portlet,
                            'view': view,
                            'adapters': adapters}
                return render("arche_pas:templates/login.pt", response, request = request)


def includeme(config):
    """ Add arche_pas.portlets to arche.includes in paster.ini if this portlet should be addable.
    """
    config.add_portlet(PASLoginPortlet)
