# -*- coding: utf-8 -*-


'''
Created on 24 janv. 2018

Basic example :
log into the agriscope server + retreive data from agribases.


@author: guillaume
'''


from agstream.session import AgspSession


session = AgspSession()
ssession = AgspSession()
session.login('masnumeriqueAgStream', '1AgStream', updateAgribaseInfo=True)

session.describe()

print ""
for abs in session.agribases :
    print abs.name
    for sensor in abs.sensors :
        print sensor.name
        df=session.getSensorDataframe(sensor)
        if df is not None :
            print df.head()
        
    
print u'Fin du programme'


'''
for abs in session.agribases :
    print abs.name
    for sensor in abs.sensors :
        print sensor.name
        df=session.getSensorDataframe(sensor)
        print df.head()
        xlsFileName = "%s.xlsx" % abs.name 
        print u"Ecriture des données %s " % xlsFileName
        df.to_excel(xlsFileName,engine='openpyxl')
'''


