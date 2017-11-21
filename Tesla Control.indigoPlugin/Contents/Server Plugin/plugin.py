#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Tesla Control plugin for indigo
# Based on sample code that is:
# Copyright (c) 2014, Perceptive Automation, LLC. All rights reserved.
# http://www.indigodomo.com

try:
    import indigo
except:
    pass
import teslajson
import json


## TODO
# 1. Exception handling
# 2. Method to set temperature (with menu for F/C)
# 3. Events and refreshing

################################################################################


class Plugin(indigo.PluginBase):
    ########################################
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
        self.vehicles = []
        self.debug = True

    ########################################
    def startup(self):
        self.debugLog("Username: %s" % self.pluginPrefs['username'])

    def getVehicles(self):
        if not self.vehicles:
            connection = teslajson.Connection(self.pluginPrefs['username'],
                                              self.pluginPrefs['password'])
            self.vehicles = dict((unicode(v['id']), v) for v in connection.vehicles)
            indigo.server.log("%i vehicles found" % len(self.vehicles))
        return self.vehicles

    # Generate list of cars
    def carListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
        cars = [(k, "%s (%s)" % (v['display_name'], v['vin']))
                for k, v in self.getVehicles().items()]
        self.debugLog("carListGenerator: %s" % str(cars))
        return cars

    ### ACTIONS
    def validateActionConfigUi(self, valuesDict, typeId, actionId):
        if typeId == 'set_charge_limit':
            try:
                percent = int(valuesDict['percent'])
                if percent > 100 or percent < 50:
                    raise ValueError
                valuesDict['percent'] = percent
            except ValueError:
                errorsDict = indigo.Dict()
                errorsDict['percent'] = "A percentage between 50 and 100"
                return (False, valuesDict, errorsDict)
        return (True, valuesDict)

    def vehicleCommand(self, action, dev):
        vehicleId = dev.pluginProps['car']
        commandName = action.pluginTypeId
        indigo.server.log("Tesla command %s for vehicle %s" % (commandName, vehicleId))
        vehicle = self.getVehicles()[vehicleId]
        if commandName == "wake_up":
            vehicle.wake_up()
            return
        data = action.props
        vehicle.command(commandName, data)

    def runConcurrentThread(self):

        try:
            while True:
                for dev in indigo.devices.iter("self"):
                    if dev.deviceTypeId == u"teslacontrol":
                        try:
                            pluginProps = dev.pluginProps
                            vehicleId = pluginProps['car']

                            vehicle = self.getVehicles()[vehicleId]
                            charge_state = vehicle.data_request('charge_state')
                            vehicle_state = vehicle.data_request('vehicle_state')
                            climate_state = vehicle.data_request('climate_state')
                            # indigo.server.log(json.dumps(charge_state))
                            # indigo.server.log(json.dumps(vehicle_state))
                            # indigo.server.log(json.dumps(climate_state))

                            pluginProps['car_version'] = vehicle_state.get('car_version', "")
                            pluginProps['vin'] = vehicle['vin']
                            pluginProps['car_type'] = vehicle_state.get('car_type', "")
                            pluginProps['vehicle_name'] = vehicle_state.get('vehicle_name', "")
                            pluginProps['wheel_type'] = vehicle_state.get('wheel_type', "")

                            keyValueList = []

                            if charge_state['charge_port_door_open']:
                                keyValueList.append({'key': 'plugged_in', 'value': True})
                            else:
                                keyValueList.append({'key': 'plugged_in', 'value': False})

                            keyValueList.append({'key': 'charging_state', 'value': charge_state['charging_state']})
                            keyValueList.append({'key': 'charge_port_door_open', 'value': charge_state['charge_port_door_open']})

                            # Store the Drive State API data
                            drive_state = vehicle.data_request('drive_state')
                            # indigo.server.log(json.dumps(drive_state))
                            keyValueList.append({'key': 'power', 'value': drive_state['power']})
                            keyValueList.append({'key': 'timestamp', 'value': drive_state['timestamp']})
                            keyValueList.append({'key': 'longitude', 'value': drive_state['longitude']})
                            keyValueList.append({'key': 'latitude', 'value': drive_state['latitude']})
                            keyValueList.append({'key': 'speed', 'value': drive_state['speed']})
                            keyValueList.append({'key': 'heading', 'value': drive_state['heading']})
                            keyValueList.append({'key': 'shift_state', 'value': drive_state['shift_state']})

                            # Store the Vehicle API Data
                            keyValueList.append({'key': 'locked', 'value': vehicle_state['locked']})

                            # Store the Climate API Data
                            keyValueList.append({'key': 'is_climate_on', 'value': climate_state['is_climate_on']})
                            keyValueList.append({'key': 'outside_temp', 'value': 9.0/5.0 * climate_state['outside_temp'] + 32}) # We use F around here
                            keyValueList.append({'key': 'inside_temp', 'value': 9.0/5.0 * climate_state['inside_temp'] + 32}) # We use F around here

                            dev.updateStatesOnServer(keyValueList)
                            dev.replacePluginPropsOnServer(pluginProps)

                        except Exception as e:
                            indigo.server.log("Error updating: {}".format(e))

                self.sleep(30)
        except self.StopThread:
            pass
