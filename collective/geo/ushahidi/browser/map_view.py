import json
import calendar
from datetime import datetime

from Acquisition import aq_inner

from zope.interface import implements
from zope.component import getMultiAdapter

from Products.Five.browser import BrowserView
from Products.CMFCore.utils import getToolByName
from Products.ATContentTypes.utils import DT2dt
from Products.AdvancedQuery import Eq, Ge, Le, In

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
        query = {'path': '/'.join(context.getPhysicalPath()),
            'portal_type': self.friendly_types(),
            'sort_on': 'start',
            'object_provides':
                'collective.geo.geographer.interfaces.IGeoreferenceable'}
        brains = catalog(**query)
        for brain in brains:
            # skip if no coordinates set
            if not brain.zgeo_geometry:
                continue

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
            # skip object w/o set start date
            start_brain = None
            for brain in brains:
                # skip if no coordinates set
                if not brain.zgeo_geometry:
                    continue

                if brain.start.year() > 1000:
                    start_brain = brain
                    break

            if start_brain:
                # now try to find last date, based on end field
                end_brain = None
                query['sort_on'] = 'end'
                query['sort_order'] = 'reverse'
                for brain in catalog(**query):
                    # skip if no coordinates set
                    if not brain.zgeo_geometry:
                        continue

                    if brain.end.year() < 2499:
                        end_brain = brain
                        break

                if not end_brain:
                    end = brains[-1].start
                else:
                    end = end_brain.end

                start = start_brain.start
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
        context = aq_inner(self.context)
        catalog = getToolByName(context, 'portal_catalog')

        # prepare catalog query
        query = Eq('path', '/'.join(context.getPhysicalPath())) & \
            In('portal_type', self.friendly_types()) & \
            Eq('object_provides',
                'collective.geo.geographer.interfaces.IGeoreferenceable')

        # apply categories
        category = self.request.get('c') and [self.request.get('c')] or []
        if category:
            query &= In('Subject', category)

        # apply content types
        if self.request.get('m'):
            query &= Eq('portal_type', self.request['m'])

        # apply 'from' date
        start = self.request.get('s')
        if start and start != '0':
            query &= Ge('end', int(start))

        # apply 'to' date
        end = self.request.get('e')
        if end and end != '0':
            query &= Le('start', int(end))

        # get zoom and calculate distance based on zoom
        zoom = self.request.get('z') and int(self.request.get('z')) or 7
        distance = float(10000000 >> zoom) / 100000.0

        # query all markers for the map
        markers = []
        for brain in catalog.evalAdvancedQuery(query, (
            ('start', 'asc'), ('end', 'desc'))):
            # skip if no coordinates set
            if not brain.zgeo_geometry:
                continue

            markers.append({
                'latitude': brain.zgeo_geometry['coordinates'][1],
                'longitude': brain.zgeo_geometry['coordinates'][0],
                'brain': brain,
            })

        # cluster markers based on zoom level
        clusters = []
        singles = []
        while len(markers) > 0:
            marker = markers.pop()
            cluster = []

            for target in markers:
                pixels = abs(marker['longitude'] - target['longitude']) + \
                    abs(marker['latitude'] - target['latitude'])

                # if two markers are closer than defined distance, remove
                # compareMarker from array and add to cluster.
                if pixels < distance:
                    markers.pop(markers.index(target))
                    cluster.append(target)

            # if a marker was added to cluster, also add the marker we were
            # comparing to
            if len(cluster) > 0:
                cluster.append(marker)
                clusters.append(cluster)
            else:
                singles.append(marker)

        # create json from clusters
        features = []
        for cluster in clusters:
            # calculate cluster center
            bounds = self.calculate_center(cluster)

            # json string for popup window
            brain = cluster[0]['brain']

            start = brain.start or ''
            if start:
                start = calendar.timegm(DT2dt(start).timetuple())

            features.append({
                'type': 'Feature',
                'properties': {
                    'id': brain.UID,
                    'name': brain.Title,
                    'link': brain.getURL(),
                    'category': brain.Subject or [],
                    'color': 'CC0000',
                    'icon': '',
                    'thumb': '',
                    'timestamp': start,
                    'count': len(cluster),
                    'class': 'stdClass'
                },
                'geometry': {
                     'type': 'Point',
                     'coordinates': [bounds['center']['longitude'],
                         bounds['center']['latitude']]
                }
            })

        # pass single points to standard markers json
        for marker in singles:
            brain = marker['brain']

            start = brain.start or ''
            if start:
                start = calendar.timegm(DT2dt(start).timetuple())

            features.append({
                'type': 'Feature',
                'properties': {
                    'id': brain.UID,
                    'name': brain.Title,
                    'link': brain.getURL(),
                    'category': brain.Subject or [],
                    'color': 'CC0000',
                    'icon': '',
                    'thumb': '',
                    'timestamp': start,
                    'count': 1,
                    'class': 'stdClass'
                },
                'geometry': brain.zgeo_geometry,
            })

        return json.dumps({"type":"FeatureCollection", "features": features})

    def calculate_center(self, cluster):
        """Calculates average lat and lon of clustered items"""
        south, west, north, east = 90, 180, -90, -180

        lat_sum = lon_sum = 0
        for marker in cluster:
            if marker['latitude'] < south:
                south = marker['latitude']

            if marker['longitude'] < west:
                west = marker['longitude']

            if marker['latitude'] > north:
                north = marker['latitude']

            if marker['longitude'] > east:
                east = marker['longitude']

            lat_sum += marker['latitude']
            lon_sum += marker['longitude']

        lat_avg = lat_sum / len(cluster)
        lon_avg = lon_sum / len(cluster)

        center = {'longitude': lon_avg, 'latitude': lat_avg}
        sw = {'longitude': west, 'latitude': south}
        ne = {'longitude': east, 'latitude': north}
        return {
            "center": center,
            "sw": sw,
            "ne": ne,
        }

    def getJSON(self):
        return json.dumps({})

    def getTimeline(self):
        # TODO: implement timeline
        return json.dumps([{"label":"All Categories","color":"#990000","data":[[1333468800000,"1"],[1358438400000,"1"]]}])

    def getJSONLayer(self):
        return json.dumps({})
