from zope.i18nmessageid import MessageFactory
w3cMessageFactory = MessageFactory('agsci.w3c')
from difflib import context_diff

def initialize(context):
    pass

class Report():

    def __init__(self, categories=[]):
        self.stats = {}
        self.diff = {}
        for c in categories:
            self.stats[c] = []
        
    def add(self, category, o):
        if not category in self.stats.keys():
            self.stats[category] = []
        self.stats[category].append(o)

    def addDiff(self, o, new, old):
        if new and old:
            self.diff[o.UID()] = "\n".join(context_diff(new.split('\n'), old.split('\n'), lineterm=''))
        
    def summary(self):
        return "\n".join(['%s : %d' % (x, len(self.stats[x])) for x in sorted(self.stats.keys())])
        
    def get(self, category):
        return self.stats.get(category, [])
        
    def categories(self):
        return self.stats.keys()
        
    def __repr__(self):
        return self.summary()

    def getDiff(self, o):
        return self.diff.get(o.UID(), "")

    def detail(self, categories=[]):
        lines = []

        if not isinstance(categories, list):
            categories = [categories]

        for k in sorted(self.categories()):
            if categories and k not in categories:
                continue
            lines.append(k)
            lines.append("="*len(k))
            for o in sorted(self.get(k), key=lambda x:x.absolute_url()):
                lines.append(o.absolute_url())
                lines.append("-"*len(o.absolute_url()))
                lines.append(self.getDiff(o))
                lines.append("")
            lines.append("")
            lines.append("")
        return "\n".join(lines)
