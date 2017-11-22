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

                            pluginProps['car_version'] = vehicle_state.get('car_version', "")
                            pluginProps['vin'] = vehicle['vin']
                            pluginProps['car_type'] = vehicle_state.get('car_type', "")
                            pluginProps['vehicle_name'] = vehicle_state.get('vehicle_name', "")
                            pluginProps['wheel_type'] = vehicle_state.get('wheel_type', "")
                            #pluginProps['batteryLevel'] = 80

                            keyvaluelist = []

                            if charge_state['charging_state'] == "Disconnected":
                                keyvaluelist.append({'key': 'plugged_in', 'value': False, 'uiValue': charge_state['charging_state']})
                                dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
                            else:
                                keyvaluelist.append({'key': 'plugged_in', 'value': True, 'uiValue': charge_state['charging_state']})
                                dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOn)

                            keyvaluelist.append({'key': 'charging_state', 'value': charge_state['charging_state']})
                            keyvaluelist.append({'key': 'charge_port_door_open', 'value': charge_state['charge_port_door_open']})

                            # Store the Drive State API data
                            drive_state = vehicle.data_request('drive_state')
                            # Get the door state data
                            keyvaluelist.append({'key': 'locked', 'value': vehicle_state['locked']})
                            keyvaluelist.append({'key': 'df', 'value': vehicle_state['df']})
                            keyvaluelist.append({'key': 'dr', 'value': vehicle_state['dr']})
                            keyvaluelist.append({'key': 'pf', 'value': vehicle_state['pf']})
                            keyvaluelist.append({'key': 'pr', 'value': vehicle_state['pr']})
                            keyvaluelist.append({'key': 'ft', 'value': vehicle_state['ft']})
                            keyvaluelist.append({'key': 'rt', 'value': vehicle_state['rt']})

                            keyvaluelist.append({'key': 'power', 'value': drive_state['power']})
                            keyvaluelist.append({'key': 'timestamp', 'value': drive_state['timestamp']})
                            keyvaluelist.append({'key': 'longitude', 'value': drive_state['longitude']})
                            keyvaluelist.append({'key': 'latitude', 'value': drive_state['latitude']})
                            keyvaluelist.append({'key': 'speed', 'value': drive_state['speed']})
                            keyvaluelist.append({'key': 'heading', 'value': drive_state['heading']})
                            keyvaluelist.append({'key': 'shift_state', 'value': drive_state['shift_state']})

                            # Store the Climate API Data
                            keyvaluelist.append({'key': 'is_climate_on', 'value': climate_state['is_climate_on']})
                            keyvaluelist.append({'key': 'outside_temp', 'value': 9.0 / 5.0 * climate_state['outside_temp'] + 32})  # We use F around here
                            keyvaluelist.append({'key': 'inside_temp', 'value': 9.0 / 5.0 * climate_state['inside_temp'] + 32})  # We use F around here

                            #dev.updateStateOnServer("charging_state", charge_state['charging_state'], uiValue=charge_state['charging_state'])
                            #indigo.server.log("Charging State: {}".format(charge_state['charging_state']))
                            #indigo.server.log("State: {}".format(dev.states))

                            #dev.updateStatesOnServer(keyvaluelist, uiValue=charge_state['charging_state'])
                            dev.updateStatesOnServer(keyvaluelist)
                            dev.replacePluginPropsOnServer(pluginProps)

                        except Exception as e:
                            indigo.server.log("Error updating: {}".format(e))

                self.sleep(30)
        except self.StopThread:
            pass
