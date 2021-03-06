# -*- coding: utf-8 -*-
"""

    
    Agriscope Session
    -----------------
    Python object allowing to connect, and download data programmaticaly from the 
    Agriscope API.


@author: renaud
"""
from __future__ import print_function
from __future__ import division

from builtins import str
from builtins import range
from past.builtins import basestring
from builtins import object
from past.utils import old_div
from agstream.devices import Agribase, Sensor
from agstream.connector import AgspConnecteur
import time
import pandas as pd
import pytz
import datetime
from datetime import timedelta
import numpy as np
from pytz import timezone


"""
  Object principal de connection avec les service Agriscoep.
  Permet de se logguer, recuperer les agribases, scanner et trouver les datasources.
"""


class AgspSession(object):
    """
    
    Main front session object:
    --------------------------
    ALlow to be authentificate, and too get Agriscope devices, and to retreive data
    as an Pandas Dataframe
    
    """

    debug = False
    """ debug flag """
    
    ms_resolution = False
    """ timestamp millisecond resoultion """
    
    agribases = list()
    """ list of agribase for the last user specified """

    def __init__(self, server="jsonapi.agriscope.fr", timezoneName=u"Europe/Paris", use_ms_resolution=False):
        self.agribases = list()
        self.connector = AgspConnecteur(server=server)
        self.set_debug(False)
        self.sessionId = 0
        self.station = False
        self.timezoneName = timezoneName
        self.tz = timezone(self.timezoneName)
        self.useInternalsSensors = False;
        self.ms_resolution = use_ms_resolution
  
    def set_debug(self, value):
        """
        Set the debug flag. More verbose
        """
        self.debug = value
        self.connector.set_debug(value)

    """
    login()
    Se loggue au service Agriscope
    Si Ok, lance la mise a jours de la liste d'agribase
    L'objectif est d'avoir la liste des agribase a jour, en particulier pour la
    date de la derniere activitée
    """

    def login(self, login_p, password_p, updateAgribaseInfo=False,showInternalsSensors=False):
        """
        Login
        =====
        Authentificate user by the Agriscope API
        If login and password are correct, the function store the user's sessionId.
        This sessionId can be used later to getAgriabse informations or to get data.
        
        :param login_p: User's login
        :param password_p : User's password
        :param updateAgribaseInfo : default: False, if True, get the last agribases 
        information from the Agriscope server.
        
        
        :return: True if login OK or False
        """
        if isinstance(login_p, str) and isinstance(password_p, str):
## removing space causing error
            login_p=login_p.replace(" ", "")
            password_p=password_p.replace(" ", "") 
        else :
            print(u"Erreur lors de la connection, login ou password doivent etre une string")
            return False
        

        status, sessionId = self.connector.login(login_p, password_p)
        self.useInternalsSensors = showInternalsSensors
        if status == True:
            # reinitialise
            self.agribases = list()
            print(login_p + u" logging OK.")
            if updateAgribaseInfo == True:
                self.__refreshAgribases()
        if self.debug == True:
            if status == True:
                print(login_p + u" logging OK.")

            else:
                print(u"Erreur de connection pour " + login_p + ".")
        self.status = status
        self.sessionId = sessionId
        return status

    """
     Retourne l'agribase par numero de serie ou string matching
     Les agribases sont considerees chargées dans le menbre self.agribases.
     Cette fonction ne va pas cherche les agribases sur le serveur
    """

    def getAgribase(self, searchPattern_p):
        """
        getAgribase
        -----------
        Tools to retreive an Agribase by name or by serialNumber in the session's
        agribase list.
        
        :param searchPattern_p: String or Int (Part of name, or Agribase serialNumber)
        
        
        :return: An agribase object corresponding to pattern, or None if not found
        """
        for abse in self.agribases:
            if isinstance(searchPattern_p, int):
                if abse.serialNumber == searchPattern_p:
                    return abse
            if isinstance(searchPattern_p, basestring):
                if searchPattern_p in abse.name:
                    return abse
        return None


    """ 
    Retourne un dataframe pour l'agribase pour la periode demandÃ©e 
    """

    def getAgribaseDataframe(self, agribase_p, from_p=None, to_p=None,index_by_sensor_id = False):
        """
        getAgribaseDataframe
        --------------------
        Return a `Pandas <https://pandas.pydata.org/>`__  Dataframe fill with data
        generated by the Agribase.
        It gets data from the Agriscope Server.
        The :timezone used is the timezone used by the session
        
        Use the period specified by the from_p and the to_p parameters.
        
        If from_p AND to_p is not specified, the period is choosen automatically from
        [now - 3 days => now]
        
        If from_p is not specified and to_p is specified, the function return a range 
        between [to_p - 3 days => to_p]
                
        :param agribase_p: Agribase object wanted.
        :param from_p: From date
        :param to_p: To date.
        
        :return: `Pandas <https://pandas.pydata.org/>`__  Dataframe with data
        """

        frame = self.getAgribaseDataframeDeep(agribase_p.serialNumber,from_p, to_p)

        if index_by_sensor_id == False : # so index with sensor name
            renaming_dict = dict()
            for col in frame.columns :
                sensor = agribase_p.getSensorByAgspSensorId(int(col))
                renaming_dict[col] = sensor.name
            frame.rename(columns=renaming_dict,inplace=True)

        if frame is not None:
            frame = frame.tz_convert(self.tz)
        return frame

    def getAgribaseDataframeDeep(self, agribase_serial_number, from_p=None, to_p=None):
        """
        getAgribaseDataframe
        --------------------
        Return a `Pandas <https://pandas.pydata.org/>`__  Dataframe fill with data
        generated by the Agribase.
        It gets data from the Agriscope Server.
        The :timezone used is the timezone used by the session
        
        Use the period specified by the from_p and the to_p parameters.
        
        If from_p AND to_p is not specified, the period is choosen automatically from
        [now - 3 days => now]
        
        If from_p is not specified and to_p is specified, the function return a range 
        between [to_p - 3 days => to_p]
                
        :param agribase_p: Agribase object wanted.
        :param from_p: From date
        :param to_p: To date.
        
        :return: `Pandas <https://pandas.pydata.org/>`__  Dataframe with data
        """
        frame = pd.DataFrame()
        frame.tz_convert(self.tz)

        if to_p == None:
            to_p = self.tz.localize(datetime.datetime.now())
        if from_p == None:
            from_p = to_p - timedelta(days=3)
        
        result_dict = self.__loadAgribaseDataFlat(agribase_serial_number,from_p,to_p) 
        for sensor_id in result_dict.keys():
            dates,values = result_dict[sensor_id]
            label= "%d"%sensor_id
            df = self.__convertDataToPandasFrame(dates, values, label)
            if df is not None and len(df) > 0:
                # print frame.head()
                frame = pd.concat([frame, df], axis=1)
        
        if frame is not None:
            frame = frame.tz_convert(self.tz)
        return frame

   

    
    """ 
    Retourne un dataframe pour l'agribase sur l'instant donnée [+/- 1 seconde]
    """

    def getAgribaseDataframeRealTime(self, agribaseSerialNumber, atDate=None):
        """
        getAgribaseDataframeRealTime
        --------------------
        Return a `Pandas <https://pandas.pydata.org/>`__  Dataframe fill with data
        generated by the Agribase.
        
                
        :param agribaseSerialNumber: Agribase serialNumber.
        :param atDate: date of the data
        
        :return: `Pandas <https://pandas.pydata.org/>`__  Dataframe with data
        """
        frame = pd.DataFrame()
        frame.tz_convert(self.tz)

        agribase = self.getAgribase(agribaseSerialNumber)
        from_p = atDate - timedelta(seconds=1);
        to_p = atDate + timedelta(seconds=1);
        result_dict = self.__loadAgribaseDataFlat(agribase.serial_number,from_p,to_p)
        for sensor_id in result_dict.keys():
            data_tuples = result_dict[sensor_id]
            sensor = agribase.getSensorByAgspSensorId(sensor_id)

        for sens in agribase.sensors:
            df = self.getSensorDataframe(sens, from_p, to_p)
            if df is not None and len(df) > 0:
                # print frame.head()
                frame = pd.concat([frame, df], axis=1)
        if frame is not None:
            frame = frame.tz_convert(self.tz)
        return frame



    """ 
    Retourne un dataframe pour le capteur pour la periode demandée 
    """

    def getSensorDataframe(self, sensor, from_p=None, to_p=None):
        """
        getSensorDataframe
        --------------------
        Return a `Pandas <https://pandas.pydata.org/>`__  Dataframe fill with data
        generated by the sensor.
        It gets data from the Agriscope Server.
        The :timezone used is the timezone used by the session
        
        Use the period specified by the from_p and the to_p parameters.
        
        If from_p AND to_p is not specified, the period is choosen automatically from
        [now - 3 days => now]
        
        If from_p is not specified and to_p is specified, the function return a range 
        between [to_p - 3 days => to_p]
                
        :param agribase_p: Agribase object wanted.
        :param from_p: From date
        :param to_p: To date.
        
        :return: `Pandas <https://pandas.pydata.org/>`__  Dataframe with data
        """
        return self.getSensorDataframeDeep(sensor.agspSensorId, sensor.name, from_p, to_p)

    def describe(self):
        """
        Return some information about the session.
        Login, Agribases count, timezone
        """
        print("login " + self.connector.lastLogin)
        print("    - " + str(len(self.agribases)) + " agribases.")
        print("    - Timezone = %s " % self.timezoneName)
        count = 0
        for abse in self.agribases:
            print("    - " + str(abse.name) + "")

    """
    Refresh information
    """

    def __refreshAgribases(self):
        json = self.connector.getAgribases(showInternalSensors=self.useInternalsSensors)
        self.agribases = list()
        for tmpjson in json["agribases"]:
            abse = Agribase()
            abse.loadFromJson(tmpjson)
            # if abse.intervalInSeconds == -1 :
            # abse.intervalInSeconds = self.connector.getAgribaseIntervaleInSeconds(abse.serialNumber)
            self.agribases.append(abse)
        return self.agribases

    def getSensorDataframeDeep(self, sensorid, sensor_name, from_p=None, to_p=None):
        if to_p == None:
            to_p = self.tz.localize(datetime.datetime.now())
        if from_p == None:
            from_p = to_p - timedelta(days=3)
        date, values = self.__loadSensorDataFlat(sensorid, from_p, to_p)
        dataFrame = self.__convertDataToPandasFrame(date, values, sensor_name)
        if dataFrame is not None:
            dataFrame = dataFrame.tz_convert(self.tz)
        return dataFrame

    def ___getAgribaseTypeName(self, serialNumber):
        url = "http://jsonmaint.agriscope.fr/tools/CHECK/agbs.php?sn=%d" % serialNumber
        json = self.connector.executeJsonRequest(url)
        returnv = -1
        if "agbsType" in json:
            returnv = json["agbsType"]
        return returnv

    def __getDataframe(self, datesArray_p, valuesArray_p, limitFrom, limitTo):
        # en python les tableaux sont des list.
        newFrame = self.convertDataToPandasFrame(
            datesArray_p, valuesArray_p, self.datasource.getSmallName()
        )
        newFrame.sort_index(inplace=True)
        if len(newFrame) > 0:
            # On borne la plage....
            # Bug du serveur ariscope... En effet parfois il renvoie des dates hors de l'intervalle demandée (par exemple 1992)
            # On limit l'effet, en 'coupant' les index dont les dates ne sont pas dans l'intervalle demane
            currentFirst = newFrame.index[0]
            currentLast = newFrame.index[len(newFrame) - 1]
            if limitFrom > currentFirst:
                newFrame = newFrame[limitFrom:currentLast]

            if limitTo < currentLast:
                newFrame = newFrame[currentFirst:limitTo]

        if len(newFrame) > 0:
            # print_full(newFrame)
            self.rawPandaDataFrame = pd.concat([self.rawPandaDataFrame, newFrame])
        return self.rawPandaDataFrame

    def __convertDataToPandasFrame(self, datesArray_p, valuesArray_p, label):
        freshDates = []
        freshValues = []
        ##print 'len(dates) : %d, len(values) : %d' % (len(datesArray_p), len(valuesArray_p))
        if len(datesArray_p) > 0:
            for i in range(len(datesArray_p)):

                dat = self.__convertUnixTimeStamp2PyDate(datesArray_p[i])
                freshDates.append(dat)
            for i in range(len(valuesArray_p)):
                freshValues.append(valuesArray_p[i])
            return pd.DataFrame(freshValues, index=freshDates, columns=[label])
            # Remove freshValue
        freshDates = []
        freshValues = []
        return None

    def __loadSensorData(self, sensor=None, from_p=None, to_p=None):
        return self.__loadSensorDataFlat(
            sensor.agspSensorId,
            self._totimestamp(from_p),
            self._totimestamp(to_p),
        )

    def __loadSensorDataFlat(self, sensorId=None, from_p=None, to_p=None):
        return self.connector.getSensorData(
            sensorId,  self._totimestamp(from_p), self._totimestamp(to_p))
        
    def __loadAgribaseDataFlat(self, agribase_sn=None, from_p=None, to_p=None):
            return self.connector.getAgribaseAllSensorsData(
            agribase_sn,  self._totimestamp(from_p), self._totimestamp(to_p))
            
        
    def _totimestamp(self, dt_obj):
        """
        Args:
            dt_obj (:class:`datetime.datetime`):

        Returns:
            int:
        """
        if not dt_obj:
            return None

        try:
            # Python 3.3+
            return int(dt_obj.timestamp())
        except AttributeError:
            # Python 3 (< 3.3) and Python 2
            return int(time.mktime(dt_obj.timetuple()))     

    def __convertUnixTimeStamp2PyDate(self, unixtimeStamp):
        """
        Convert a unixtime stamp (provenant du serveur agriscope) en Temps python avec une timezone UTC
        """
        #
        # Comportement bizarre de sync 1199/thermomètre(-485966252) Marsillargues Marseillais Nord(1199) T° AIR °C no user parameter
        # lors de la syncrhonination de base de l'univers
        # il y a vait:
        # unixtimestamp=1412937447499
        # unixtimestamp=1412937832500
        # unixtimestamp=1404910637499
        # unixtimestamp=-30373006607501
        # ======================================================================
        # ERROR: test_firstUnivers (tests.agspUniversTests.TestAgspUnivers)
        # ----------------------------------------------------------------------
        # Traceback (most recent call last):
        #  File "C:\Users\guillaume\Documents\Developpement\django\trunk\datatooling\pandas\tests\agspUniversTests.py", line 37, in test_firstUnivers
        # print unixtimeStamp
        if unixtimeStamp < 0:
            unixtimeStamp = 1
        # print "unixtimestamp=" + unicode(unixtimeStamp)
        #print("unixtimestamp %f, %.2f, %.4f"% (unixtimeStamp,old_div(unixtimeStamp, 1000),unixtimeStamp/ 1000) )
        if self.ms_resolution == True :
            returnv = pytz.utc.localize(
            datetime.datetime.utcfromtimestamp(unixtimeStamp/ 1000)
            )
        else :
            returnv = pytz.utc.localize(
            datetime.datetime.utcfromtimestamp(old_div(unixtimeStamp, 1000))
            )
        #print (returnv.strftime("%d/%m/%y %HH%mm%Ss%f"))
        # print unicode(returnv)
        # print "%s" % returnv.year
        # if (returnv.year == 1992) :

        # print "%d %s" % (unixtimeStamp, unicode(returnv))
        return returnv


def _touchLogin(self, login_p, password_p):
    status, sessionId = self.connector.login(login_p, password_p)
    self.status = status
    self.sessionId = sessionId
