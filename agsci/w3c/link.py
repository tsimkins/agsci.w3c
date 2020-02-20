try:
    from zope.app.component.hooks import getSite
except ImportError:
    from zope.component.hooks import getSite

from agsci.w3c.site import translateURL

from zope.component import getSiteManager
from zope.component import getUtility
from Products.CMFCore.utils import getToolByName

import transaction

from Testing.makerequest import makerequest
from zope.app.component.hooks import setSite
from Products.agCommon import getPloneSites, sortFolder, replaceTag
from agsci.w3c.content import getText, setText

import urllib2
from urllib2 import URLError, HTTPError
from httplib import InvalidURL
from BeautifulSoup import BeautifulSoup

from urlparse import urljoin


def findBrokenLinks(
    context, redirects={}, shortened=[],
    url_pattern=None, debug=False, contentFilter={}
):

    # Return Codes dict
    return_codes = {}

    # Stuff known redirects and shortened into return codes
    for url in redirects.keys():
        return_codes[url] = 302

    for url in shortened:
        return_codes[url] = 200

    # Actual method for checking a link.  Inside the findBrokenLinks function
    # because we need access to the return_codes, etc. structures and I didn't
    # want to make them global in the module.

    def checkLink(url, cgi=False, anchors=False):

        original_url = url

        # Strip params unless cgi is set to True
        if not cgi and '?' in url:
            url = url.split('?')[0]

        if not anchors and '#' in url:
            url = url.split('#')[0]

        if url.startswith('mailto:'):
            return 200

        if not url.startswith('http'):
            return 500

        if not return_codes.get(url):
            try:
                data = urllib2.urlopen(url, None, 30)
            except ValueError:
                return_codes[url] = 999
            except HTTPError:
                return_codes[url] = 404
            except:
                return_codes[url] = 999
            else:
                if data.getcode() == 200:
                    if url == data.geturl():
                        return_codes[url] = 200
                    elif data.geturl().startswith('http://www.psu.edu/search/gss/'):
                        return_codes[url] = 404
                    else:
                        if 'utm_' in data.geturl() or 'webaccess.psu.edu' in data.geturl():
                            # Treat Google Analytics tracked as 200's, don't modify
                            # Same for links requiring login
                            return_codes[url] = 200
                        else:
                            return_codes[url] = 302
                            redirects[url] = data.geturl()
                            redirects[original_url] = data.geturl()
                else:
                    return_codes[url] = data.getcode()
                    if data.getcode() in [301,302]:
                        redirects[url] = data.geturl()
                        redirects[original_url] = data.geturl()

        return_codes[original_url] = return_codes[url]
        return return_codes[url]


    # Calculate sanitized URL method
    def filterURL(base_url, url):

        site = getSite()

        if url.startswith('mailto:'):
            return None

        if not (url.startswith('http:') or url.startswith('https:')):
            # Calculate relative URL, replace ../ because Plone folders don't
            # end with /

            if url.startswith(site.absolute_url()):
                url = url.replace(site.absolute_url(), '')

            url = urljoin(base_url, url)

            if '../' in url:
                url = url.replace('../', '')

        # Skip URLs not matching URL pattern
        if url_pattern and url_pattern not in url.lower():
            return None
        else:
            return url

    # Plone site and search path
    site = getSite()
    search_path = "/".join(context.getPhysicalPath())
    portal_catalog = getToolByName(site, "portal_catalog")

    # Return list headers
    outfile = [['Type', 'State', 'Object URL', 'Link URL', 'Status', 'Redirect']]

    urls = []

    # Get link objects
    _q = {
        'portal_type' : 'Link',
        'path' : search_path
    }

    _q.update(contentFilter)

    results = portal_catalog.searchResults(_q)

    for r in results:
        try:
            o = r.getObject()
        except KeyError:
            continue
        base_url = translateURL(o)

        url = filterURL(base_url, o.remoteUrl)

        if url:
            urls.append([r.Type, r.review_state, base_url, url])


    # Get links in text

    _q = {
        'portal_type' : [
            'Document',
            'Event',
            'Folder',
            'HomePage',
            'News Item',
            'Topic',
        ],
        'path' : search_path
    }

    _q.update(contentFilter)

    results = portal_catalog.searchResults()

    for r in results:
        try:
            o = r.getObject()
        except KeyError:
            continue

        base_url = translateURL(o)

        text = getText(o)

        try:
            soup = BeautifulSoup(text)
        except TypeError:
            continue

        for a in soup.findAll('a'):
            url = filterURL(base_url, a.get('href', ''))

            if url:
                urls.append(["%s [LINK]" % r.Type, r.review_state, base_url, url])

        for img in soup.findAll('img'):
            url = filterURL(base_url, img.get('src', ''))

            if url:
                urls.append(["%s [IMAGE]" % r.Type, r.review_state, base_url, url])


    for (portal_type, review_state, base_url, url) in urls:
        print "Checking %s" % url
        status = checkLink(url)

        redirect = redirects.get(url, '')

        if debug or status != 200:
            outfile.append([portal_type, base_url, url, str(status), redirect])


    return outfile
