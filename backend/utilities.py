from private_keys import GOOGLE_MAPS_API_KEY

import httplib2
import json

import sys
import codecs
sys.stdout = codecs.getwriter('utf8')(sys.stdout)
sys.stderr = codecs.getwriter('utf8')(sys.stderr)


# Use Google Maps to convert a location into Latitute/Longitute coordinates
# return status, latitude, longitude
def getGeocodeLocation(inputString):

	# Prepare url
	# FORMAT: https://maps.googleapis.com/maps/api/geocode/json?address=1600+Amphitheatre+Parkway,+Mountain+View,+CA&key=API_KEY
	locationString = inputString.replace(" ", "+")
	url = ('https://maps.googleapis.com/maps/api/geocode/json?address=%s&key=%s'% (locationString, GOOGLE_MAPS_API_KEY))
	h = httplib2.Http()

	# Perform request & handle response
	MAPS_TAG = "Google Geocode Api: "
	try:
		response, content = h.request(url,'GET')
		if response.status==200:
			print MAPS_TAG + "Success"
		else:
			print MAPS_TAG + "Server error"
			return (response.status, None, None)
	except httplib2.ServerNotFoundError:
		print MAPS_TAG + "Server not responding"
		return (-1, None, None)

	# Handle json
	result = json.loads(content)
	if len(result['results']) == 0:
		return (200, None, None)
	latitude = result['results'][0]['geometry']['location']['lat']
	longitude = result['results'][0]['geometry']['location']['lng']
	return (200, latitude, longitude)
