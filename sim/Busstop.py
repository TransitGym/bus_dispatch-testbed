import xml.etree.ElementTree as ET
import numpy as np
from random import seed
from random import gauss,randint
from sim.Passenger import Passenger

class Bus_stop():
    def __init__(self,id,lat,lon  ):
        '''

        :param id: bus stop unique id
        :param lat:  bus stop latitude in real-world
        :param lon:  bus stop longitude in real-world
        :param routes: bus stop serving routes set
        :param waiting_list:  waitting passenger list in this stop
        :param dyna_arr_rate:  dynamic passenger arrival rate for this stop
        :param arr_bus_load:  record arrving bus load
        :param arr_log:  (dictionay) record bus arrival time with respect to each route (route id is key)
        :param uni_arr_log: (list) record bus arrival time
        :param dep_log: (dictionay) record bus departure time with respect to each route (route id is key)
        :param uni_dep_log: (list) record bus departure time

        '''

        self.id = id
        self.lat = lat
        self.lon = lon
        self.loc = 0.
        self.next_stop = None
        self.prev_stop = None
        self.routes = []
        self.waiting_list=[]
        self.dyna_arr_rate = []
        self.dyna_arr_rate_sp ={}
        # self.type = 0
        # self.demand = 0
        self.arr_bus_load =[]
        self.arr_log = {}
        self.uni_arr_log = []
        self.dep_log = {}
        self.uni_dep_log = []
        self.pax = {}
        self.dest = {}
        self.served = 0

        self.is_first_stop = False
        self.is_last_stop = False

        from collections import OrderedDict
        self.dest = OrderedDict()

        self.pre_gen_pax_list = {}
        self.cum_arr = 0
        self.cum_dep = 0
        self.arrivals = {}
        self.actual_departures = {}
        self.actual_arrivals = {}
        self.rate = 1.0  # pax/sec

        self.in_stop_bus = None
        self.waiting_bus = []

        self.historical_pax = []

    # return a list of passengers arrival time
    def pax_gen(self,bus,sim_step=0):

        pax = []
        base=0
        interval = 0
        self.arr_bus_load.append(len(bus.onboard_list))
        if bus!=None:
            if len(self.arr_log[bus.route_id])>1:
                interval = (self.arr_log[bus.route_id][-1] -self.arr_log[bus.route_id][-2] )
                sample = (np.random.poisson(self.rate*self.dyna_arr_rate[int(sim_step/3600)%24]+0.0001,int(interval)  ))
                base=self.arr_log[bus.route_id][-2]
                for i in range(sample.shape[0]):
                    if sample[i]>0:
                        pax+=[base+i for t in range(sample[i])]
            else:
                # assume passenger will gather in less than 15min before the first bus began.
                sample = (np.random.poisson(self.rate*self.dyna_arr_rate[int(sim_step/3600)%24]+0.0001,900 ))
                base = self.arr_log[bus.route_id][-1]
                for i in range(sample.shape[0]):
                    if sample[i]>0:
                        pax+=[base-i for t in range(sample[i])]
        else:
            for k,v in self.arr_log.items():
                interval = sim_step - v[-1]
                sample = (np.random.poisson(self.rate*self.dyna_arr_rate[int(sim_step/3600)%24],int(interval) ))
                base = v[-1][1]
                for i in range(sample.shape[0]):
                    if sample[i] > 0:
                        pax += [base + i for t in range(sample[i])]

        return  pax

    def pax_gen_sp(self,bus,sim_step=0):
        pax = []
        base = 0
        interval = 0
        self.arr_bus_load.append(len(bus.onboard_list))
        if bus != None:
            if len(self.arr_log[bus.route_id]) > 1:
                interval = (self.arr_log[bus.route_id][-1] - self.arr_log[bus.route_id][-2])
                sample = (np.random.poisson(self.rate * self.dyna_arr_rate_sp[bus.route_id][int(sim_step / 3600) % 24] + 0.0001,
                                            int(interval)))
                base = self.arr_log[bus.route_id][-2]
                for i in range(sample.shape[0]):
                    if sample[i] > 0:
                        pax += [base + i for t in range(sample[i])]
            else:
                # assume passenger will gather in less than 15min before the first bus began.
                sample = (np.random.poisson(self.rate * self.dyna_arr_rate_sp[bus.route_id][int(sim_step / 3600) % 24] + 0.0001, 900))
                base = self.arr_log[bus.route_id][-1]
                for i in range(sample.shape[0]):
                    if sample[i] > 0:
                        pax += [base - i for t in range(sample[i])]
        else:
            for k, v in self.arr_log.items():
                interval = sim_step - v[-1]
                sample = (np.random.poisson(self.rate * self.dyna_arr_rate_sp[bus.route_id][int(sim_step / 3600) % 24], int(interval)))
                base = v[-1][1]
                for i in range(sample.shape[0]):
                    if sample[i] > 0:
                        pax += [base + i for t in range(sample[i])]

        return pax
    def set_rate(self,r ):
        self.rate =r # pax/sec

    def pax_read(self,bus,sim_step=0):
        pax = []
        base = 0
        interval = 0

        self.arr_bus_load.append(len(bus.onboard_list))
        if len(self.arr_log[bus.route_id]) > 1:
            interval = (self.arr_log[bus.route_id][-1]  - self.arr_log[bus.route_id][-2] )
            base = self.arr_log[bus.route_id][-2]
        else:
            base = 0

        leave=[]
        for p_id,p in self.pax.items():
            if p.plan_board_time>base and p.plan_board_time<=sim_step and p.dest in bus.left_stop:
                p.took_bus = bus.id
                leave.append(p_id)
                if base>0:
                    p.arr_time = base+np.random.randint(0,sim_step-base)
                else:
                    p.arr_time = p.plan_board_time
                pax.append(p)

        return pax

    def pax_gen_od(self,bus,sim_step=0,dest_id=None):
        base=0
        interval = 0

        if bus!=None:
            if len(self.arr_log[bus.route_id])>1:
                interval = (self.arr_log[bus.route_id][-1] -self.arr_log[bus.route_id][-2] )
                sample = (np.random.poisson(self.rate*(self.dest[dest_id][int(sim_step/3600)%24])+0.0001,int(interval)  ))
                base=self.arr_log[bus.route_id][-2]
                pax = [ ]
                for i in range(sample.shape[0]):
                    if sample[i]>0:
                        pax+=[base+i for t in range(sample[i])]
            else:
                # assume passenger will gather in less than 15min before the first bus began.
                sample = (np.random.poisson(self.rate*(self.dest[dest_id][int(sim_step/3600)%24])+0.0001,900 ))

                base = self.arr_log[bus.route_id][-1]
                pax = [ ]
                for i in range(sample.shape[0]):
                    if sample[i]>0:
                        pax+=[base-i for t in range(sample[i])]
        else:
            for k,v in self.arr_log.items():
                interval = sim_step - v[-1]
                sample = (np.random.poisson(self.rate*self.dest[dest_id][int(sim_step/3600)%24],int(interval) ))

                base = v[-1][1]
                for i in range(sample.shape[0]):
                    if sample[i] > 0:
                        pax += [base + i for t in range(sample[i])]

        return  pax

    def pre_pax_gen(self, begin=6 * 3600, demand_impulse_rate=0.):
        flag = 0
        arr_cum = 0
        # train/test under uncertainty
        arr = []
        while int(begin / 3600) < 23:
            temp_pre_gen_pax_list = []
            times = []
            interval = 60
            for dest_id in self.dest.keys():
                scales = np.clip(np.random.normal(2., demand_impulse_rate), a_min=1.5, a_max=10.)
                mu = self.dest[dest_id][int(begin / 3600) % 24]
                arr_rate = mu * scales
                pax = []
                if flag == 0:
                    sample = np.random.poisson((arr_rate + 0.00005) * interval, int(900 / interval))
                    for i in range(sample.shape[0]):
                        if sample[i] > 0:
                            pax += [begin + 3600 - np.random.randint(i * interval, (i+1) * interval) for t in range(sample[i])]
                else:
                    sample = np.random.poisson((arr_rate + 0.00005) * interval, int(3600 / interval))

                    for i in range(sample.shape[0]):
                        if sample[i] > 0:
                            pax += [begin + np.random.randint(i * interval, (i+1) * interval) for t in range(sample[i])]

                current_num = len(self.pre_gen_pax_list)
                for i in range(len(pax)):
                    p = Passenger(origin=str(self.id), arr_time=pax[i], id=current_num + i)
                    p.dest = str(dest_id)
                    self.pre_gen_pax_list[current_num + i] = p
                    arr.append(pax[i])
                # arr_cum+=1
                # self.arrivals[times[i]] = arr_cum

            begin += 3600
            flag = 1

        # print(np.mean(arr), np.max(arr), np.min(arr), np.median(arr), len(arr))
    def get_pax(self, bus=None, sim_step=0):

        pax = []
        if bus is not None:
            for k in range(len(self.pre_gen_pax_list)):
                if self.pre_gen_pax_list[k].arr_time <= sim_step and self.pre_gen_pax_list[k].born == 0:
                    self.pre_gen_pax_list[k].born = 1
                    pax.append(self.pre_gen_pax_list[k])
        else:
            for k in range(len(self.pre_gen_pax_list)):
                if self.pre_gen_pax_list[k].arr_time <= sim_step and self.pre_gen_pax_list[k].born == 0:
                    pax.append(self.pre_gen_pax_list[k])

        return pax

if __name__ == '__main__':
    seed(1)
    # generate some integers
    r = 1. / randint(160, 240)
    for _ in range(10):
        for _ in range(10):
            value =  max(gauss(r,0.0004),0.00002)
            print(value*3600)
        print('--')