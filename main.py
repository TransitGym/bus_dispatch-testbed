import argparse
import os, sys
from sim import Sim_Engine
from sim import util as U
import numpy as np
import pandas as pd
import copy
import time
from random import randint
from random import seed
import torch
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description='param')
parser.add_argument("--seed", type=int, default=1)               # random seed
parser.add_argument("--model", type=str, default='caac')         # caac ddpg maddpg
parser.add_argument("--data", type=str, default='SG_22_1')       # data prefix
parser.add_argument("--para_flag", type=str, default='SG_22_1')  # parameter prefix
parser.add_argument("--episode", type=int, default=401)          # training episode
parser.add_argument("--overtake", type=int, default=0)           # overtake=0: not allow overtaking between buses
parser.add_argument("--restore", type=int, default=1)            # restore=1: restore the model
parser.add_argument("--all", type=int, default=1)                # all=0 for considering only forward/backward buses' all=1 for all buses
parser.add_argument("--vis", type=int, default=0)

args = parser.parse_args()



def run(args ):
    stop_list, pax_num = U.getStopList(args.data)
    print('Stops prepared, total bus stops: %g' % (len(stop_list)))
    bus_routes = U.getBusRoute(args.data)
    print('Bus routes prepared, total routes :%g' % (len(bus_routes)))
    dispatch_times, bus_list, route_list, simulation_step = U.init_bus_list(bus_routes)
    print('init...')
    # two line
    back_bus_stop_list = {}
    teminal = None
    for bus_stop_id, bus_stop in stop_list.items():
        if bus_stop.next_stop is not None:
            back_bus_stop_list[str(int(bus_stop_id) * 100)] = copy.deepcopy(bus_stop)
            back_bus_stop_list[str(int(bus_stop_id) * 100)].id = int(bus_stop_id) * 100
        else:
            bus_stop.next_stop = int(bus_stop.prev_stop) * 100
            bus_stop.is_last_stop = True
            teminal = bus_stop.id
            continue
        if bus_stop.prev_stop is not None:
            back_bus_stop_list[str(int(bus_stop_id) * 100)].next_stop = int(bus_stop.prev_stop) * 100
        if bus_stop.next_stop is not None:
            back_bus_stop_list[str(int(bus_stop_id) * 100)].prev_stop = int(bus_stop.next_stop) * 100
        if bus_stop.prev_stop is None:
            back_bus_stop_list[str(int(bus_stop_id) * 100)].next_stop = None
            bus_stop.is_first_stop = True
    stop_list.update(back_bus_stop_list)
    print('total bus stops: %g' % (len(stop_list)))
    eng = Sim_Engine.Engine(bus_list=bus_list,
                            busstop_list=stop_list,
                            dispatch_times=dispatch_times,
                            demand=0,
                            simulation_step=simulation_step,
                            route_list=route_list,
                            is_allow_overtake=args.overtake,
                            terminal=teminal
                            )
    for _, stop in eng.busstop_list.items():
        # update dest
        stop.dest = {}
        next_stop = stop.next_stop
        while next_stop is not None:
            stop.dest[str(next_stop)] = [0.000001 for _ in range(24)]
            next_stop = eng.busstop_list[str(next_stop)].next_stop
            if next_stop is not None and eng.busstop_list[str(next_stop)].is_last_stop == True:
                break

    bus_list_clean = eng.bus_list
    bus_stop_list_clean = eng.busstop_list


    now_ = time.time()

    for ep in range(args.episode):
        now_ep = time.time()
        stop_list_ = copy.deepcopy(bus_stop_list_clean)
        bus_list_ = copy.deepcopy(bus_list_clean)

        eng = Sim_Engine.Engine(bus_list=bus_list_,
                                busstop_list=stop_list_,
                                dispatch_times=dispatch_times,
                                demand=0,
                                simulation_step=simulation_step,
                                route_list=route_list,
                                is_allow_overtake=args.overtake,
                                terminal=teminal
                                )
        demand_impulse_rate = np.random.randint(0, 50) / 10.

        for _, stop in eng.busstop_list.items():
            stop.pre_pax_gen(demand_impulse_rate=demand_impulse_rate)

        Flag = True
        begin = time.time()
        control = None
        T = 0
        while Flag:
            if T == 2000:
                control = '70299'
            Flag = eng.sim(control=control)
            T+=1

        log = eng.cal_statistic(name=str(args.para_flag))

        abspath = os.path.abspath(os.path.dirname(__file__))
        name = abspath + "/log/" + args.data

        U.train_result_track(eng=eng, ep=ep,  log=log, name=name,
                             seed=args.seed)

        U.visualize_trajectory(engine=eng)

        print('Total time cost:%g sec Episode time cost:%g' % (time.time() - now_, time.time() - now_ep))
        print('')



if __name__ == '__main__':
    seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    run(args)





