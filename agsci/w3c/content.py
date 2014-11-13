from Products.CMFCore.utils import getToolByName
from BeautifulSoup import BeautifulSoup, Tag, NavigableString

try:
    from zope.app.component.hooks import getSite
except ImportError:
    from zope.component.hooks import getSite

from agsci.w3c import Report
import re




def setText(object, text):
    if object.portal_type in ['Folder', 'PhotoFolder'] or object.meta_type in ['Blog', 'Subsite', 'Section', 'ATFolder', 'PhotoFolder', 'FormFolder']:
        try:
            object.folder_text.update(text, object)
        except AttributeError:
            pass
    elif object.portal_type in ['FSDPerson']:
        object.setBiography(text)
    elif object.portal_type in ['File', 'Image', 'Link', 'FSDFacultyStaffDirectoryTool'] or object.portal_type.startswith('Form'):
        pass
    else:
        object.setText(text)
    object.reindexObject()


def getText(object):
    if object.portal_type in ['Folder', 'PhotoFolder'] or object.meta_type in ['Blog', 'Subsite', 'Section', 'ATFolder', 'PhotoFolder', 'FormFolder']:
        try:
            text = object.folder_text()
        except AttributeError:
            text = ""
    elif object.portal_type in ['File', 'Image', 'Link', 'FSDFacultyStaffDirectoryTool'] or object.portal_type.startswith('Form'):
        text = ''
    elif object.portal_type in ['FSDPerson']:
        text = object.getBiography()
    elif hasattr(object, 'getRawText'):
        text = object.getRawText()
    elif hasattr(object, 'getText'):
        text = object.getText()
    else:
        text = ""
    return text


def getItemsWithText(context):
    portal_catalog = getToolByName(context, "portal_catalog")

    return portal_catalog.searchResults({'portal_type' : ['News Item', 'Event', 'Document', 'Folder', 'Topic', 'HomePage', 'PhotoFolder', 'FSDPerson']})

def fixHeadingTags(context, dry_run=True):
    report = Report(categories=['headingsOK', 'headingsBold', 'headingsItalic', 'headingsBr'])

    def getNewTag(tag, heading):
        tag_regex = re.compile("</*%s>" % tag, re.I|re.M)
        return BeautifulSoup(tag_regex.sub('', str(heading))).contents[0]

    for r in getItemsWithText(context):
        o = r.getObject()
        text = getText(o)
        soup = BeautifulSoup(text)
        old_soup = soup.prettify()
        found_italic = False
        found_bold = False
        found_br = False
        
        for htag in ['h2', 'h3']:
            for h in soup.findAll(htag):
                for t in ['strong', 'b']:
                    if h(t):
                        found_bold = True
                        h.replaceWith(getNewTag(t, h))

                for t in ['br']:
                    for tag in h(t):
                        found_br = True
                        tag.extract()

                for t in ['em', 'i']:
                    if h(t):
                        # This is a special case, since we may legitimately have
                        # italicized words (latin names, etc.) inside headers.
                        # Only if it's going to be a dry run do we modify the 
                        # HTML so we can report on it.
                        if dry_run:
                            found_italic = True
                            h.replaceWith(getNewTag(t, h))
                        

        if found_bold:
            report.add('headingsBold', o)

        if found_italic:
            report.add('headingsItalic', o)
            
        if found_br:
            report.add('headingsBr', o)
            
        if found_bold or found_br or found_italic:
            new_soup = soup.prettify()
            report.addDiff(o, old_soup, new_soup)

            if not dry_run:
                setText(o, new_soup)

    return report

def fixPotentialHeadings(context, dry_run=True):
    report = Report(categories=['hasAutoFixableHeadings', 'hasManualFixableHeadings', 'noHeadings'])

    for r in getItemsWithText(context):
        o = r.getObject()
        text = getText(o)
        soup = BeautifulSoup(text)
        old_soup = soup.prettify()
        found_auto=False
        found_manual=False
        replaced_text = []

        for p in soup.findAll('p'):
            for c in ['\n', '\r', '\r\n']:
                while c in p.contents:
                    p.contents.remove(c)
            if len(p.contents) == 1:
                if isinstance(p.contents[0], Tag):
                    if p.contents[0].name in ['strong', 'b'] and len(p.contents[0]) == 1:
                        if not (soup('h2') or soup('h3')):
                            found_auto=True
                            p.replaceWith(BeautifulSoup('<h2>%s</h2>' % p.contents[0].text))
                            replaced_text.append(p.contents[0].text)
                        else:
                            found_manual=True

        if found_auto:
            report.add('hasAutoFixableHeadings', o)
        elif found_manual:
            report.add('hasManualFixableHeadings', o)
        else:
            report.add('noHeadings', o)

        if found_auto:
            new_soup = soup.prettify()
            report.addDiff(o, old_soup, new_soup)
        
            if not dry_run:
                setText(o, new_soup)

    return report



def fixH2H3(context, dry_run=True):

    h3 = re.compile(r"<(/*)h3(.*?)>")

    report = Report(categories=['rightHeadings', 'wrongHeadings', 'noHeadings'])

    for r in getItemsWithText(context):
        o = r.getObject()
        text = getText(o)

        try:
            soup = BeautifulSoup(text)
            old_soup = soup.prettify()
        except TypeError:
            import pdb; pdb.set_trace()
        if soup('h2'):
            report.add('rightHeadings', o)
        elif soup('h3'):
            report.add('wrongHeadings', o)
        else:
            report.add('noHeadings', o)

        for o in report.get('wrongHeadings'):
            text = getText(o)
            new_soup = BeautifulSoup(text).prettify()
            old_soup = new_soup
            new_soup = h3.sub(r"<\g<1>h2\g<2>>", new_soup)
            report.addDiff(o, old_soup, new_soup)
            if not dry_run:
                setText(o, new_soup)

    return report


def fixOtherHeadingLevels(context, dry_run=True):

    report = Report(categories=['goodHeadings', 'badHeadings', 'goodAndBadHeadings', 'noHeadings', 'tooManyHeadings'])

    good_headings = set(['h2', 'h3'])
    bad_headings = set(['h1', 'h4', 'h5', 'h6'])
    all_headings = list(good_headings.union(bad_headings))


    for r in getItemsWithText(context):
        o = r.getObject()
        text = getText(o)
        
        headings = {}

        try:
            soup = BeautifulSoup(text)
        except TypeError:
            import pdb; pdb.set_trace()

        has_good = has_bad = False

        for h in all_headings:
            heading_count = len(soup(h))
            if heading_count:
                headings[h] = heading_count
                if h in good_headings:
                    has_good = True
                elif h in bad_headings:
                    has_bad = True
        
        if has_good and has_bad:
            report.add('goodAndBadHeadings', o)
        elif has_good:
            report.add('goodHeadings', o)
        elif has_bad:
            report.add('badHeadings', o)
        else:                
            report.add('noHeadings', o)

        if len(headings.keys()) > 3:
            report.add('tooManyHeadings', o)
        elif has_bad:
            if len(headings.keys()) == 3:
                headings_to_fix = sorted(headings.keys())
                heading_replacements = zip(headings_to_fix, ['h2', 'h3', 'h4'])
            elif len(headings.keys()) == 2:
                headings_to_fix = sorted(headings.keys())
                heading_replacements = zip(headings_to_fix, ['h2', 'h3'])
            else:
                heading_replacements = [(headings.keys()[0], 'h2'),]

            old_soup = soup.prettify()
            new_soup = old_soup
            for (from_h, to_h) in heading_replacements:
                if from_h == to_h:
                    continue
                replaceHeading = re.compile(r"<(/*)%s(.*?)>" % from_h)
                new_soup = replaceHeading.sub(r'<\1%s>' % to_h, new_soup)                
            if old_soup != new_soup:
                report.addDiff(o, old_soup, new_soup)
                if not dry_run:
                    setText(o, new_soup)
            
            
    return report


def fixLinkText(context, dry_run=True):

    report = Report(categories=['noLinks', 'okLinks', 'brokenLinks'])

    for r in getItemsWithText(context):
        o = r.getObject()
        text = getText(o)
        soup = BeautifulSoup(text)
        old_soup = soup.prettify()
        found_link = False
        found_empty_link = False
        found_no_links = False

        if soup('a'):
            for a in soup.findAll('a'):
                link_text = ""
                url_link = False
                empty_link = False
                for i in a.contents:
                    if isinstance(i, NavigableString):
                        link_text = i
                    else:
                        link_text = str(i)

                    if link_text and 'http://' in link_text or 'https://' in link_text:
                        found_link = True
                        url_link = True
                    elif not link_text:
                        found_link = True
                        found_empty_link = True
                        empty_link = True

                if url_link:
                    a.contents.append(NavigableString(' -- REPLACE WITH CORRECT LINK TEXT'))
                if empty_link:
                    a.contents.append(NavigableString('-- EMPTY LINK --'))
        else:
            found_no_links = True

        if found_no_links:
            report.add('noLinks', o)
        elif found_link:
            report.add('brokenLinks', o)
            new_soup = soup.prettify()
            report.addDiff(o, old_soup, new_soup)
        else:
            report.add('okLinks', o)

        # Note: emptyLinks are also included in broken links.
        if found_empty_link:
            report.add('emptyLinks', o)


    return report


def fixResolveUID(context, dry_run=True):

    portal_catalog = getToolByName(context, 'portal_catalog')
    report = Report(categories=['hasResolveUID', 'brokenResolveUID', 'noResolveUID'])

    uids = {}
    site_url = getSite().absolute_url()
    
    def getURLByUIDLink(uid):
        # Preparsing
        anchor = ''
        image_size = ''
        
        if '#' in uid:
            (uid,anchor)  = uid.split('#')[0:2]
            if anchor:
                anchor = '#%s' % anchor

        if '/image_' in uid or '/leadImage_' in uid:
            (uid,image_size)  = uid.split('/')[0:2]
            if image_size:
                image_size = '/%s' % image_size
                
        if uids.get(uid):
            return uids[uid]
        else:
            results = portal_catalog.searchResults({'UID' : uid})

            if results:
                url = results[0].getURL().replace(site_url, '', 1)
                uids[uid] = "".join([url, image_size, anchor])
            else:
                uids[uid] = None

            return uids[uid]

    for r in getItemsWithText(context):
        o = r.getObject()
        text = getText(o)
        has_uid = False
        broken_uid = False

        soup = BeautifulSoup(text)

        old_soup = soup.prettify()

        for a in soup('a'):
            href = a.get('href', '')
            if href.startswith('resolveuid/'):
                uid = href.replace('resolveuid/', '')
                url = getURLByUIDLink(uid)
                if url:
                    a['href'] = url
                    has_uid = True
                else:
                    url = "NOT_FOUND"
                    broken_uid = True
                print "A   %s -> %s" % (uid, url)

        for i in soup('img'):
            src = i.get('src', '')
            if src.startswith('resolveuid/'):
                uid = src.replace('resolveuid/', '')
                url = getURLByUIDLink(uid)
                if url:
                    i['src'] = url
                    has_uid = True
                else:
                    url = "NOT_FOUND"
                    broken_uid = True
                print "IMG %s -> %s" % (uid, url)

        if broken_uid:
            report.add('brokenResolveUID', o)

        if has_uid:
            report.add('hasResolveUID', o)
            new_soup = soup.prettify()
            report.addDiff(o, old_soup, new_soup)
            if not dry_run:
                setText(o, new_soup)
                o.reindexObject()
        else:
            report.add('noResolveUID', o)

    return report
