import json
import calendar
from datetime import datetime

from Acquisition import aq_inner

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

        categories = set() # to store unique object keywords
        ctypes = [] # to store portal type and it's title
        ctypes_added = [] # to avoid duplicates in content types list
        ctypes_meta = {} # to cache portal type Titles
        brains = catalog(path='/'.join(context.getPhysicalPath()),
            portal_type=self.friendly_types(), sort_on='effective')
        for brain in brains:
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

        # sort our data
        categories = list(categories)
        categories.sort()

        ctypes = list(ctypes)
        ctypes.sort(lambda x,y:cmp(x['title'], y['title']))

        # prepare dates, for this we just generate range of years and months
        # between first and last item fetched list of objects
        dates = []
        if len(brains) > 0:
            # skip object w/o set effective date
            start_brain = None
            for brain in brains:
                if brain.effective.year() > 1000:
                    start_brain = brain
                    break

            if start_brain:
                start, end = start_brain.effective, brains[-1].effective
                first_year, last_year = start.year(), end.year()
                first_month, last_month = start.month(), end.month()

                for year in range(first_year, last_year+1):
                    months = []

                    # count from first month only for first year
                    month_from = 1
                    if year == first_year:
                        month_from = first_month

                    # count till last month only for last year
                    month_to = 12
                    if year == last_year:
                        month_to = last_month

                    for month in range(month_from, month_to+1):
                        dt = datetime(year, month, 1)
                        months.append({
                            'datetime': dt,
                            'label': '%s %s' % (dt.strftime('%b'), year),
                            'timestamp': calendar.timegm(dt.timetuple()),
                        })

                    dates.append((year, months))

            # sort by year
            if dates:
                dates.sort(lambda x,y: cmp(x[0], y[0]))

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
