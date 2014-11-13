from Products.CMFCore.utils import getToolByName

try:
    from zope.app.component.hooks import getSite
except ImportError:
    from zope.component.hooks import getSite

from agsci.w3c.site import translateURL
from agsci.subsite.events import getPortletAssignmentMapping

def findBrokenPortlets(context, types=['Document', 'HomePage', 'Folder', 'Blog', 'Subsite', 'Section', 'Topic', 'Newsletter', 'Blog']):
    site = getSite()
    search_path = "/".join(context.getPhysicalPath())

    portal_catalog = getToolByName(site, "portal_catalog")
    urltool = getToolByName(site, "portal_url")
    
    results = portal_catalog.searchResults({'portal_type' : types, 'path' : search_path})
    
    portlet_managers = ['plone.leftcolumn', 'plone.rightcolumn', 'agcommon.centercolumn', 'agcommon.rightcolumn']
    
    broken = []
    
    for r in results:
        o = r.getObject()
        for i in portlet_managers:
            pm = getPortletAssignmentMapping(o, i)
            for pid in pm.keys():
                p = pm[pid]
                klass = str(p.__class__)
                path = ""
                feeds = ""
                portlet_type = ""
                found = False
                if 'plone.portlet.collection.collection.Assignment' in klass:
                    path = p.target_collection
                    found = True
                    title = p.title
                    portlet_type = "Collection"
                elif 'collective.portlet.feedmixer.portlet.Assignment' in klass:
                    path = p.target_collection
                    found = True
                    title = p.title
                    if p.feeds:
                        feeds = "|".join(p.feeds.split())
                    portlet_type = "Feedmixer"
                elif 'plone.app.portlets.portlets.navigation.Assignment' in klass:
                    path = p.root
                    found = True
                    title = p.name
                    portlet_type = "Navigation"
                if path:
                    if path.startswith('/'):
                        path = path.replace('/', '', 1)
                    try:
                        target = site.restrictedTraverse(path)
                    except (AttributeError, KeyError):
                        broken.append(["BROKEN URL", translateURL(o, https=True), title, path, i, klass])
                if found and feeds:
                    broken.append(["MANUAL CHECK", translateURL(o, https=True), title, feeds, i, klass])
    
    return broken
