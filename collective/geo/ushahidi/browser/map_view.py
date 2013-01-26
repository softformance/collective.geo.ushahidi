import json

from Acquisition import aq_inner
from DateTime import DateTime

from zope.interface import implements
from zope.component import getMultiAdapter

from Products.Five.browser import BrowserView
from Products.CMFCore.utils import getToolByName

from plone.memoize.instance import memoize

from .interfaces import IUshahidiMapView


class UshahidiMapView(BrowserView):

    implements(IUshahidiMapView)

    def friendly_types(self):
        pstate = getMultiAdapter((self.context, self.request),
            name=u'plone_portal_state')
        return pstate.friendly_types()

    @memoize
    def getObjectsInfo(self):
        context = aq_inner(self.context)
        catalog = getToolByName(context, 'portal_catalog')
        portal_types = getToolByName(context, 'portal_types')

        categories = set()
        ctypes = []
        ctypes_added = []
        ctypes_meta = {}
        years = {}
        for brain in catalog(path='/'.join(context.getPhysicalPath()),
            portal_type=self.friendly_types(),
            sort_on='created'):

            # populate categories
            if brain.Subject:
                categories |= set(brain.Subject)

            # populate types
            ptype = brain.portal_type
            if ptype not in ctypes_added:
                ctypes_added.append(ptype)
                if ptype in ctypes_meta:
                    title = ctypes_meta[ptype]
                else:
                    title = portal_types.getTypeInfo(ptype).title
                    ctypes_meta[ptype] = title
                ctypes.append({'id': ptype, 'title': title})

            # save creation date
            created = brain.created
            year = years.setdefault(created.year(), [])
            # TODO: add month only once for found object
            year.append({
                'datetime': created,
                'label': '%s %s' % (created.aMonth(), created.year()),
                # TODO: convert to timestamp
                'timestamp': str(DateTime('%s/01/%s' % (created.month(),
                    created.year()))),
            })

        # sort our data
        categories = list(categories)
        categories.sort()

        ctypes = list(ctypes)
        ctypes.sort(lambda x,y:cmp(x['title'], y['title']))

        dates = [(k, v) for k, v in years.items()]
        dates.sort()

        return {
            'categories': tuple(categories),
            'types': tuple(ctypes),
            'dates': tuple(dates),
        }

    def getDates(self):
        return self.getObjectsInfo()['dates']

    def getTypes(self):
        return self.getObjectsInfo()['types']

    def getCategories(self):
        """Returns list of keywords used in sub-objects of context"""
        return self.getObjectsInfo()['categories']

    def getJSONCluster(self):
        return json.dumps({"type":"FeatureCollection","features":[{"type":"Feature","properties":{"id":"1","name":"<a href='http://210.71.197.91/ushahidi/reports/view/1'>Hello Ushahidi!</a>","link":"http://210.71.197.91/ushahidi/reports/view/1","category":[0],"color":"CC0000","icon":"","thumb":"","timestamp":1333544071,"count":1,"class":"stdClass"},"geometry":{"type":"Point","coordinates":["36.8214511820082","-1.28730007070501"]}},{"type":"Feature","properties":{"id":"2","name":"<a href='http://210.71.197.91/ushahidi/reports/view/2'>Report 1</a>","link":"http://210.71.197.91/ushahidi/reports/view/2","category":[0],"color":"CC0000","icon":"","thumb":"","timestamp":1358514060,"count":1,"class":"stdClass"},"geometry":{"type":"Point","coordinates":["36.825142","-1.298412"]}}]})

    def getJSON(self):
        return json.dumps({})

    def getTimeline(self):
        return json.dumps([{"label":"All Categories","color":"#990000","data":[[1333468800000,"1"],[1358438400000,"1"]]}])

    def getJSONLayer(self):
        return json.dumps({})
