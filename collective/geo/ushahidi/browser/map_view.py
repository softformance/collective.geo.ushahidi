import json

from zope.interface import implements

from Products.Five.browser import BrowserView

from .interfaces import IUshahidiMapView


class UshahidiMapView(BrowserView):

    implements(IUshahidiMapView)

    def getJSONCluster(self):
        return json.dumps({"type":"FeatureCollection","features":[{"type":"Feature","properties":{"id":"1","name":"<a href='http:\/\/210.71.197.91\/ushahidi\/reports\/view\/1'>Hello Ushahidi!<\/a>","link":"http:\/\/210.71.197.91\/ushahidi\/reports\/view\/1","category":[0],"color":"CC0000","icon":"","thumb":"","timestamp":1333544071,"count":1,"class":"stdClass"},"geometry":{"type":"Point","coordinates":["36.8214511820082","-1.28730007070501"]}},{"type":"Feature","properties":{"id":"2","name":"<a href='http:\/\/210.71.197.91\/ushahidi\/reports\/view\/2'>Report 1<\/a>","link":"http:\/\/210.71.197.91\/ushahidi\/reports\/view\/2","category":[0],"color":"CC0000","icon":"","thumb":"","timestamp":1358514060,"count":1,"class":"stdClass"},"geometry":{"type":"Point","coordinates":["36.825142","-1.298412"]}}]})

    def getJSON(self):
        return json.dumps({})

    def getTimeline(self):
        return json.dumps([{"label":"All Categories","color":"#990000","data":[[1333468800000,"1"],[1358438400000,"1"]]}])

    def getJSONLayer(self):
        return json.dumps({})
