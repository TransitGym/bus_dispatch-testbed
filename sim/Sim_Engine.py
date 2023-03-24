import copy
import math
import numpy as np
import pandas as pd
import time
from sim.Bus import Bus
from sim.Passenger import Passenger
from sim.Route import Route


class Engine():
    def __init__(self, bus_list, busstop_list, route_list, simulation_step, dispatch_times, demand=0, agents=None,
                 is_allow_overtake=0, terminal=None):

        self.terminal = terminal
        self.busstop_list = busstop_list
        self.simulation_step = simulation_step
        self.pax_list = {}  # passenger on road
        self.arr_pax_list = {}  # passenger finihsed trip
        self.dispatch_buslist = {}
        self.agents = {}
        self.route_list = route_list
        self.dispatch_buslist = {}
        self.is_allow_overtake = is_allow_overtake
        self.agents = agents
        self.bus_list = bus_list
        self.bunching_times = 0
        self.arrstops = 0
        self.demand = demand
        self.records = []
        self.step = 0
        self.dispatch_times = dispatch_times

        self.rs = {}

        self.arrivals = {}
        #TODO paxenger demand of the back bus stop

        self.bus_hash = {}
        k = 0
        for bus_id, bus in self.bus_list.items():
            self.bus_hash[bus_id] = k
            k += 1

        self.mh = {}
        for rid, t in self.dispatch_times.items():
            self.mh[rid] = np.mean(np.array(t[1:]) - np.array(t[:-1]))

    def cal_statistic(self, name, train=1):
        print('total pax:%d' % (len(self.pax_list)))
        wait_cost = []
        travel_cost = []
        headways_var = {}
        headways_mean = {}
        boards = []
        still_wait = 0
        stop_wise_wait = {}
        delay = []
        miss = [0.]
        for pax_id, pax in self.pax_list.items():
            w = min(pax.onboard_time - pax.arr_time, self.simulation_step - pax.arr_time)
            miss.append(pax.miss)
            wait_cost.append(w)
            if pax.origin in stop_wise_wait:
                stop_wise_wait[pax.origin].append(w)
            else:
                stop_wise_wait[pax.origin] = [w]
            if pax.onboard_time < 99999999:
                boards.append(pax.onboard_time)
                if pax.alight_time < 999999:
                    travel_cost.append(pax.alight_time - pax.onboard_time)
                    delay.append(pax.alight_time - pax.arr_time - pax.onroad_cost)
            else:
                still_wait += 1

        print('MISS:%g' % (np.max(miss)))
        for bus_id, bus in self.bus_list.items():
            tt = []

            stop_wise_wait_order = []
            arr_times = []
            buslog = pd.DataFrame()
            for bus_stop_id in bus.pass_stop:
                buslog[str(bus_stop_id)] = self.busstop_list[str(bus_stop_id)].arr_log[bus.route_id]
                arr_times.append([str(bus_stop_id)] + self.busstop_list[str(bus_stop_id)].arr_log[bus.route_id])
                if str(bus_stop_id) in stop_wise_wait:
                    stop_wise_wait_order.append(np.mean(stop_wise_wait[str(bus_stop_id)]))

        arr_times = []

        buslog = pd.DataFrame()
        for bus_stop_id in bus.pass_stop:
            bus_stop_id = str(bus_stop_id)
            buslog[bus_stop_id] = self.busstop_list[bus_stop_id].arr_log[bus.route_id]
            arr_times.append([bus_stop_id] + self.busstop_list[bus_stop_id].arr_log[bus.route_id])

            try:
                stop_wise_wait_order.append(np.mean(stop_wise_wait[bus_stop_id]))
            except:
                stop_wise_wait_order.append(0)

            for k, v in self.busstop_list[bus_stop_id].arr_log.items():
                v = sorted(v)
                h = np.array(v)[1:] - np.array(v)[:-1]
                if np.isnan(np.var(h)):
                    continue
                try:
                    headways_var[bus_stop_id].append(np.var(h))
                    headways_mean[bus_stop_id].append(np.mean(h))
                except:
                    headways_var[bus_stop_id] = [np.var(h)]
                    headways_mean[bus_stop_id] = [np.mean(h)]
        log = {}
        log['wait_cost'] = wait_cost
        log['travel_cost'] = travel_cost
        log['headways_var'] = headways_var
        log['headways_mean'] = headways_mean
        log['stw'] = stop_wise_wait_order
        log['bunching'] = self.bunching_times
        log['delay'] = delay
        print('bunching times:%g headway mean:%g hedaway var:%g EV:%g' % (
            self.bunching_times, np.mean(list(headways_mean.values())), np.mean(list(headways_var.values())),
            (np.mean(list(headways_var.values())) / (np.mean(list(headways_mean.values())) ** 2))))

        AWT = []
        AOD = []
        for k in bus.pass_stop:
            k = str(k)
            if math.isnan(np.var(self.busstop_list[k].arr_bus_load) / np.mean(self.busstop_list[k].arr_bus_load)):
                AOD.append(0)
            else:
                AOD.append(np.var(self.busstop_list[k].arr_bus_load) / np.mean(self.busstop_list[k].arr_bus_load))
            if k in stop_wise_wait:
                AWT.append(np.mean(stop_wise_wait[k]))


        log['sto'] = AOD
        log['AOD'] = np.mean(AOD)
        print('AWT:%g' % (np.mean(wait_cost)))
        print('AOD:%g' % (np.mean(AOD)))
        print('headways_var:%g' % (np.sqrt(np.mean(list(headways_var.values())))))
        log['arr_times'] = arr_times
        return log

    def serve_by_presetOD(self, bus, stop):
        board_cost = 0
        alight_cost = 0
        wait_num = 0
        if bus is not None:
            alight_pax = bus.pax_alight_fix(stop, self.pax_list)
            for p in alight_pax:
                self.pax_list[p].alight_time = self.simulation_step
                bus.onboard_list.remove(p)
                self.arr_pax_list[p] = self.pax_list[p]

            alight_cost = len(alight_pax) * bus.alight_period

            # boarding procedure

            new_pax = stop.get_pax(bus, sim_step=self.simulation_step)


            num = len(self.pax_list) + 1
            for k in range(len(new_pax)):
                p = new_pax[k]
                p.id = num
                self.pax_list[num] = p
                self.pax_list[num].took_bus = bus.id
                self.pax_list[num].route = bus.route_id
                self.busstop_list[str(stop.id)].waiting_list.append(num)
                self.busstop_list[str(stop.id)].historical_pax.append(num)
                num += 1
            self.busstop_list[str(stop.id)].cum_arr += len(new_pax)

            pax_leave_stop = []
            waiting_list = sorted(self.busstop_list[str(stop.id)].waiting_list)[:]
            wait_num = len(waiting_list)
            arr = []
            for num in waiting_list:
                if bus is not None and self.pax_list[num].route == bus.route_id:
                    self.pax_list[num].miss += 1
                if bus is not None and bus.capacity > len(bus.onboard_list) and \
                        self.pax_list[num].route == bus.route_id:
                    self.pax_list[num].onboard_time = self.simulation_step
                    arr.append(self.pax_list[num].arr_time)
                    bus.onboard_list.append(num)
                    board_cost += bus.board_period
                    pax_leave_stop.append(num)
                    self.busstop_list[str(stop.id)].cum_dep += 1

            for num in pax_leave_stop:
                self.busstop_list[str(stop.id)].waiting_list.remove(num)

        self.busstop_list[str(stop.id)].actual_departures[self.simulation_step] = self.busstop_list[str(stop.id)].cum_dep
        self.busstop_list[str(stop.id)].actual_arrivals[self.simulation_step] = self.busstop_list[str(stop.id)].cum_arr
        return alight_cost, board_cost, wait_num

    def update_left_stop(self, curr_stop, direction=0):
        next_stop = curr_stop.next_stop
        left_stop = []
        if direction == 0:
            while next_stop is not None:
                left_stop.append(str(next_stop))
                next_stop = self.busstop_list[str(next_stop)].next_stop
                if next_stop is None:
                    break
        elif direction == 1:
            while next_stop != self.terminal:
                left_stop.append(str(next_stop))
                next_stop = self.busstop_list[str(next_stop)].next_stop
            left_stop.append(str(next_stop))
        return left_stop

    def sim(self, control=None):
        for bus_id, bus in self.bus_list.items():
            if bus.is_dispatch == 0 and bus.dispatch_time <= self.simulation_step:
                bus.is_dispatch = 1
                if bus.is_virtual != 1:
                    bus.current_speed = bus.speed * np.random.randint(60., 120.) / 100.
                else:
                    bus.current_speed = bus.speed * 0.8
                self.dispatch_buslist[bus_id] = bus
            if bus.is_dispatch == 1 and len(self.dispatch_buslist[bus_id].left_stop) <= 0:
                bus.is_dispatch = -1
                self.dispatch_buslist.pop(bus_id, None)

        for bus_id, bus in self.dispatch_buslist.items():
            if bus.backward_bus != None and self.bus_list[bus.backward_bus].is_dispatch == -1:
                bus.backward_bus = None
            if bus.forward_bus != None and self.bus_list[bus.forward_bus].is_dispatch == -1:
                bus.forward_bus = None

        for bus_id, bus in self.dispatch_buslist.items():
            bus.serve_remain = max(bus.serve_remain - 1, 0)
            bus.hold_remain = max(bus.hold_remain - 1, 0)

            if bus.is_virtual == 1 and bus.arr == 0 and abs(bus.loc[-1] - bus.stop_dist[bus.left_stop[0]]) < bus.speed:
                curr_stop = self.busstop_list[bus.left_stop[0]]
                bus.serve_remain = 0
                bus.pass_stop.append(curr_stop.id)
                bus.left_stop = bus.left_stop[1:]
                bus.arr = 1

            if bus.is_virtual == 0 and bus.arr == 0 and abs(bus.loc[-1] - bus.stop_dist[str(bus.left_stop[0])]) < bus.speed:
                if str(bus.left_stop[0]) not in self.busstop_list:
                    self.busstop_list[str(bus.left_stop[0])] = self.busstop_list[str(bus.left_stop[0]).split('_')[0]]

                curr_stop = self.busstop_list[bus.left_stop[0]]
                self.busstop_list[str(bus.left_stop[0])].arr_bus_load.append(len(bus.onboard_list))
                if bus.route_id in self.busstop_list[str(curr_stop.id)].arr_log:
                    self.busstop_list[str(curr_stop.id)].arr_log[bus.route_id].append(
                        self.simulation_step)
                else:
                    self.busstop_list[str(curr_stop.id)].arr_log[bus.route_id] = [
                        self.simulation_step]
                # board_cost, alight_cost = self.serve(bus, curr_stop)
                alight_cost, board_cost, wait_num = self.serve_by_presetOD(bus, curr_stop)
                bus.arr = 1
                bus.serve_remain = max(board_cost, alight_cost) + 1.

                bus.stay[str(curr_stop.id)] = 1
                bus.cost[str(curr_stop.id)] = bus.serve_remain
                bus.pass_stop.append(curr_stop.id)
                # determine the left stops again
                # update loc with the parallel stop with opposite direction then update the left stops
                if control is not None:
                    split_point = control
                    if bus.left_stop[0] == split_point:
                        if bus.loc[-1] < self.busstop_list[self.terminal].loc:
                            bus.loc[-1] = bus.stop_dist[str(int(int(bus.left_stop[0])*100))]
                            curr_stop = self.busstop_list[str(int(int(bus.left_stop[0])*100))]
                            bus.left_stop = self.update_left_stop(curr_stop, direction=0)
                        elif bus.loc[-1] > self.busstop_list[self.terminal].loc:
                            bus.loc[-1] = bus.stop_dist[str(int(int(bus.left_stop[0]) / 100))]
                            curr_stop = self.busstop_list[str(int(int(bus.left_stop[0]) / 100))]
                            bus.left_stop = self.update_left_stop(curr_stop, direction=1)
                    else:
                        bus.left_stop = bus.left_stop[1:]
                else:
                    bus.left_stop = bus.left_stop[1:]


                if len(bus.pass_stop) > 1 and self.dispatch_times[bus.route_id].index(
                        bus.dispatch_time) > 0:
                    if self.simulation_step in self.arrivals:
                        self.arrivals[self.simulation_step].append([curr_stop.id, bus_id, len(bus.onboard_list)])
                    else:
                        self.arrivals[self.simulation_step] = [[curr_stop.id, bus_id, len(bus.onboard_list)]]

            if bus.serve_remain > 0:
                bus.stop()
            else:
                if self.is_allow_overtake == 1:
                    bus.dep()
                else:
                    if bus.forward_bus in self.dispatch_buslist and bus.speed + bus.loc[-1] >= \
                            self.dispatch_buslist[bus.forward_bus].loc[-1]:
                        bus.stop()
                        bus.current_speed = bus.speed * np.random.randint(60, 120) / 100.
                        if bus.b == 0:
                            self.bunching_times += 1
                            bus.b = 1
                    else:
                        bus.b = 0
                        bus.dep(bus.current_speed)
                        for p in bus.onboard_list:
                            self.pax_list[p].onroad_cost += 1
                        if len(bus.pass_stop) > 0:
                            if bus.route_id in self.busstop_list:
                                self.busstop_list[str(bus.pass_stop[-1])].dep_log[bus.route_id].append(
                                    [bus.id, self.simulation_step])
                            else:
                                self.busstop_list[str(bus.pass_stop[-1])].dep_log[bus.route_id] = [
                                    [bus.id, self.simulation_step]]

        self.simulation_step += 1

        Flag = False
        for bus_id, bus in self.bus_list.items():
            if bus.is_dispatch != -1:
                Flag = True

        return Flag

    def control(self, bus, type=0):
        return

    def cal_headway(self, bus):

        if bus.forward_bus is not None and bus.forward_bus in self.dispatch_buslist:
            fh = abs(bus.loc[-1] - self.bus_list[bus.forward_bus].loc[-1]) / bus.c_speed

        else:
            fh = abs(bus.loc[-1] - 0.) / bus.c_speed

        if bus.backward_bus is not None and bus.backward_bus in self.dispatch_buslist:
            bh = abs(bus.loc[-1] - self.bus_list[bus.backward_bus].loc[-1]) / bus.c_speed

        else:
            bh = abs(bus.loc[-1] - 0.) / bus.c_speed

        return fh, bh

    def route_info(self, bus):
        fh = [500 for _ in range(3)]
        bh = [500 for _ in range(3)]
        for bus_id, bus_ in self.dispatch_buslist.items():
            if bus_.route_id == bus.route_id:
                if bus_.forward_bus != None and bus_.forward_bus in self.dispatch_buslist:
                    fh.append(abs(bus_.loc[-1] - self.bus_list[bus_.forward_bus].loc[-1]) / bus_.speed)
                if bus_.backward_bus != None and bus_.backward_bus in self.dispatch_buslist:
                    bh.append(abs(bus_.loc[-1] - self.bus_list[bus_.backward_bus].loc[-1]) / bus_.speed)

        if len(bh) < 2:
            return 999999, 999999

        return np.var(bh), np.mean(bh)
