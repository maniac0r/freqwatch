#!/usr/bin/env python2
# freqwatch v0.2
#
# Joshua Davis (freqwatch -*- edgetera.net)
# Copyright(C) 2014
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from __future__ import division

import cgi
import MySQLdb
import math
import os
import signal
import sys
import threading
import time
from iniparse import INIConfig
from rtlsdr import RtlSdr
from subprocess import Popen, PIPE

try:
    from gps import *
    gps_imported = True
except:
    gps_imported = False

sigint_handled = False
stop = threading.Event()

BLACKLIST_FILE = 'blacklist'
CLIENTID_LEN   = 64
CONF_FILE      = 'freqwatch.conf'
ERR            = 1
FW_VERSION     = 'v0.2'
GPS_SLEEP      = 5 # seconds


class Scanner():
    def __init__(self, devid, freqs, squelch, ppm, gpsp, config):
        self.devid = devid
        self.freqs = freqs
        self.squelch = squelch
        self.ppm = ppm
        self.delay = float(config.rtl.collection_delay)
        self.db_scan_table = config.db.db_scan_table

        self.cmd = config.rtl.rtl_path+'/rtl_power'
        self.clientid = config.rtl.clientid[:CLIENTID_LEN]

        self.using_gps = False
        if int(config.gps.gpsd) == 1 and gps_imported == True:
            self.using_gps = True
            self.gpsp = gpsp

        self.devnull = open(os.devnull, 'w')

        try:
            db_ip = config.db.db_ip
            db_port = int(config.db.db_port)
            db_user = config.db.db_user
            db_pass = config.db.db_pass
            db_db = config.db.db_db

            self.db = MySQLdb.connect(host=db_ip, port=db_port, user=db_user, \
                                        passwd=db_pass, db=db_db)

            self.db.autocommit(False)
            self.cursor = self.db.cursor()

        except MySQLdb.Error, e:
            print("MySQL Error [{}]: {}".format(e.args[0], e.args[1]))
            sys.exit(ERR)

        self.sql = ('INSERT INTO {} (date, time, freq, power, clientid, gps) VALUES ''(%s, %s, %s, %s, %s, %s)'.format(self.db_scan_table))

        # blacklist
        self.blacklist = list()
        blines = None
        try:
            with open(BLACKLIST_FILE) as bfile:
                blines = bfile.readlines()

        except:
            print("Could not import from blacklist file {}".format(BLACKLIST_FILE))

        if blines != None:
            for b in blines:
                if b[0] == '#' or '-' not in b:
                    continue

                try:
                    f1, f2 = b.split('-')
                    self.blacklist.append([int(f1), int(f2)])
                except:
                    pass


    def worker(self):
        print("Scanner thread running for device {}".format(self.devid))

        while not stop.isSet():
            p = Popen([self.cmd, "-d {}".format(self.devid), "-f {}".format(self.freqs), \
                    "-1", "-p {}".format(self.ppm)], stdout=PIPE, stderr=self.devnull)

            data = p.communicate()[0].strip()
            rc = p.returncode

            if rc != 0:
                print("rtl-power exited with error code that was not 0({}); "\
                        "thread terminating".format(rc))

            if self.using_gps == True:
                gpsstr = self.gpsp.get_current()
                if gpsstr == None:
                    gpsstr = ''
            else:
                gpsstr = 'disabled'

            for tmp in data.split('\n'):
                if stop.isSet():
                    return

                try:
                    d, t, freq_low, freq_high, freq_step, samples, \
                            raw_readings = tmp.split(', ', 6)
                    freq_low = float(freq_low)
                    freq_step = float(freq_step)

                    readings = [x.strip() for x in raw_readings.split(',')]
                except:
                    print("thread exiting on exception")
                    sys.exit(0)

                for i in range(len(readings)):
                    f = freq_low+(freq_step*i)

                    if self.blacklisted(f) == True:
                        continue

                    r = float(readings[i])

                    if r > self.squelch:
                        self.insertdb(d, t, f, r, gpsstr)

            self.db.commit()
            time.sleep(self.delay)

        return


    def blacklisted(self, freq):
        for b in self.blacklist:
            if freq > b[0] and freq < b[1]:
                return True

        return False


    def insertdb(self, d, t, freq, power, gpsstr):
        try:
            self.cursor.execute(self.sql, (d, t, freq, power, self.clientid, gpsstr))

        except MySQLdb.Error, e:
            self.db.rollback()
            print("MySQL Error [{}]: {}".format(e.args[0], e.args[1]))
            sys.exit(ERR)


class GpsPoller(threading.Thread):
    def __init__(self, host, port):
        threading.Thread.__init__(self)
        self.gpsd = gps(host, port, mode=WATCH_ENABLE)
        self.locstr = None


    def get_current(self):
        return self.locstr


    def run(self):
        try:
            while not stop.isSet():
                self.current_value = self.gpsd.next()
                self.locstr = str(self.gpsd.fix.latitude)+' '+str(self.gpsd.fix.longitude)
                time.sleep(GPS_SLEEP)
        except StopIteration:
            pass


def main():
    config = INIConfig(open(CONF_FILE))

    scanners = config.rtl.scanners
    if type(scanners) != type(str()):
        print("No scanners defined in the configuration file.")
        sys.exit(ERR)

    if int(config.gps.gpsd) == 1 and gps_imported == True:
        gpsp = GpsPoller(config.gps.gpsd_ip, config.gps.gpsd_port)
        gpsp.start()
    else:
        gpsp = None

    threads = list()
    devs = list()
    for s in scanners.split(','):
        devid = s.strip()
        if len(devid) == 0:
            continue

        if int(devid) in devs:
            print("You already have assigned the device id {}".format(devid))
            sys.exit(ERR)
        devs.append(int(devid))

        a = 'config.rtl.scanner'+s
        tmp = eval(a)

        freqs, squelch, ppm = tmp.split('/')
        if freqs == None:
            print("Is there a frequency entry for each device you've " \
                    "specified in 'scanners' in the configuration?")
            sys.exit(ERR)

        freqs = freqs.strip()
        squelch = int(squelch.strip())
        ppm = ppm.strip()
        if len(ppm) == 0:
            ppm = 0
        else:
            ppm = int(ppm)

        clientid = config.rtl.clientid

        sworker = Scanner(devid, freqs, squelch, ppm, gpsp, config)
        thread = threading.Thread(target=sworker.worker)
        threads.append(thread)
        thread.start()

    for t in threads:
        t.join()


def sigint_handler(signal, frame):
    global sigint_handled

    if sigint_handled == False:
        print("SIGINT received.  Stopping...")
        stop.set()
        sigint_handled = True


if __name__ == '__main__':
    signal.signal(signal.SIGINT, sigint_handler)
    main()

