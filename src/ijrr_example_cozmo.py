#!/usr/bin/env python
'''
.. module:: ijrr_example_cozmo
   :synopsis: Defines the case study presented in the IJRR journal paper.

.. moduleauthor:: Cristian Ioan Vasile <cvasile@bu.edu>
'''

'''
    Defines the case study presented in the IJRR journal paper.
    Copyright (C) 2014-2016  Cristian Ioan Vasile <cvasile@bu.edu>
    Hybrid and Networked Systems (HyNeSs) Group, BU Robotics Laboratory,
    Boston University

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import os, sys
import logging
import itertools as it

import numpy as np

from spaces.base import Workspace, line_translate
from spaces.maps2d import BallRegion2D, BoxRegion2D, PolygonRegion2D, \
                          expandRegion, BoxBoundary2D, BallBoundary2D, Point2D
from robots import Cozmo, CozmoSensor

from planning import RRGPlanner, LocalPlanner, Request
from models import IncrementalProduct, compute_potentials
from graphics.planar import addStyle, Simulate2D, to_rgba
from lomap import Timer


def caseStudy():
    ############################################################################
    ### Output and debug options ###############################################
    ############################################################################
    outputdir = os.path.abspath('../data_ijrr/example2')
    if not os.path.isdir(outputdir):
        os.makedirs(outputdir)
    
    # configure logging
    fs, dfs = '%(asctime)s %(levelname)s %(message)s', '%m/%d/%Y %I:%M:%S %p'
    loglevel = logging.DEBUG
    logfile = os.path.join(outputdir, 'ijrr_example_2.log')
    verbose = True
    logging.basicConfig(filename=logfile, level=loglevel, format=fs,
                        datefmt=dfs)
    if verbose:
        root = logging.getLogger()
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(loglevel)
        ch.setFormatter(logging.Formatter(fs, dfs))
        root.addHandler(ch)
    
    
    ############################################################################
    ### Define case study setup (robot parameters, workspace, etc.) ############
    ############################################################################
    
    # define robot diameter (used to compute the expanded workspace)
    robotDiameter = 0.036
    
    # define boundary
    boundary = BoxBoundary2D([[0, 4.8], [0, 3.6]])
    # define boundary style
    boundary.style = {'color' : 'black'}
    # create expanded region
    eboundary = BoxBoundary2D(boundary.ranges +
                                np.array([[1, -1], [1, -1]]) * robotDiameter/2)
    eboundary.style = {'color' : 'black'}
    
    # create robot's workspace and expanded workspace
    wspace = Workspace(boundary=boundary)
    ewspace = Workspace(boundary=eboundary)
    
    # create robot object
    robot = Cozmo('Cozmo', init=Point2D((2, 2)), wspace=ewspace, stepsize=0.999)
    robot.diameter = robotDiameter
    robot.localObst = 'local_obstacle'
    
    logging.info('Conf space: %s', robot.cspace)
    
    # create simulation object
    sim = Simulate2D(wspace, robot, ewspace)
    sim.config['output-dir'] = outputdir
    sim.config['background'] = os.path.abspath('../data_ijrr/imMap.png')
    
    # regions of interest
    R1 = (BoxRegion2D([[1.0, 2.0], [0.2, 0.8]], ['r1']), 'brown')
    R2 = (BallRegion2D([4.2, 0.7], 0.3, ['r2']), 'green')
    R3 = (BoxRegion2D([[3.7, 4.5], [1.5, 2.3]], ['r3']), 'red')
    R4 = (BoxRegion2D([[0.7 , 1.4], [1.8, 2.3]], ['r4']), 'magenta')
    # global obstacles
    O1 = (PolygonRegion2D([[0.0, 1.6], [0.7, 1.34], [0.7, 1.19], [0.0, 1.34]],
                          ['o1']), 'gray')
    O2 = (PolygonRegion2D([[1.3, 1.33], [2.6, 1.2], [2.19, 1.06], [1.3, 1.1]],
                          ['o2']), 'gray')
    O3 = (PolygonRegion2D([[3.54, 1.27], [4.8, 1.52], [4.8, 1.3], [3.44, 1.08]],
                          ['o3']), 'gray')
    O4 = (BoxRegion2D([[0, 4.8], [2.5, 3.6]], ['o4']), 'gray')
    
    # add all regions
    regions = [R1, R2, R3, R4, O1, O2, O3, O4]
    
    # add regions to workspace
    for r, c in regions:
        # add styles to region
        addStyle(r, style={'facecolor': c})
        # add region to workspace
        sim.workspace.addRegion(r)
        # create expanded region
        er = expandRegion(r, robot.diameter/2)
        # add style to the expanded region
        addStyle(er, style={'facecolor': c})
        # add expanded region to the expanded workspace
        sim.expandedWorkspace.addRegion(er)
    
    # local  requests
    F1 = (BallRegion2D([3.24, 1.98], 0.3, ['fire']), ('orange', 0.5))
    F2 = (BallRegion2D([1.26, 0.48], 0.18, ['fire']), ('orange', 0.5))
    S2 = (BallRegion2D([4.32, 1.48], 0.27, ['survivor']), ('yellow', 0.5))
    requests = [F1, F2, S2]
    # define local specification as a priority function
    localSpec = {'survivor': 0, 'fire': 1}
    logging.info('Local specification: %s', localSpec)
    localSpec_cube_color = {'survivor': 3, 'fire': 2}
    # local obstacles
    obstacles = []
    
    # add style to local requests and obstacles
    for r, c in requests:
        # add styles to region
        addStyle(r, style={'facecolor': to_rgba(*c)}) #FIMXE: HACK
        r.cube_color = localSpec_cube_color[next(iter(r.symbols))]
    
    # create request objects
    reqs = []
    for r, _ in requests:
        name = next(iter(r.symbols))
        reqs.append(Request(r, name, localSpec[name]))
    requests = reqs
    obstacles = [o for o, _, _ in obstacles]
    
    # set the robot's sensor
    sensingShape = BallBoundary2D([0, 0], 0.5)
    robot.sensor = CozmoSensor(robot, sensingShape, requests, obstacles)
    
    # display workspace
    sim.display()
     
    # display expanded workspace
    sim.display(expanded=True)
    
    ############################################################################
    ### Generate global transition system and off-line control policy ##########
    ############################################################################
    
    globalSpec = ('[] ( (<> r1) && (<> r2) && (<> r3) && (<> r4)'
                  + ' && !(o1 || o2 || o3 || o4))')
    logging.info('Global specification: %s', globalSpec)
    
    # initialize incremental product automaton
    checker = IncrementalProduct(globalSpec) #, specFile='ijrr_globalSpec.txt')
    logging.info('Buchi size: (%d, %d)', checker.buchi.g.number_of_nodes(),
                                         checker.buchi.g.number_of_edges())
    
    # initialize global off-line RRG planner
    sim.offline = RRGPlanner(robot, checker, None, iterations=1000)
    sim.offline.eta = [0.5, 1.0] # good bounds for the planar case study
    
    with Timer():
        if sim.offline.solve():
            logging.info('Found solution!')
        else:
            logging.info('No solution found!')
            return
    
    logging.info('Finished in %d iterations!', sim.offline.iteration)
    logging.info('Size of TS: %s', sim.offline.ts.size())
    logging.info('Size of PA: %s', sim.offline.checker.size())
    
    # save global transition system and control policy
    sim.offline.ts.save(os.path.join(outputdir, 'ts.yaml'))
    
    ############################################################################
    ### Display the global transition system and the off-line control policy ###
    ############################################################################
    
    # display workspace and global transition system
    prefix, suffix = sim.offline.checker.globalPolicy(sim.offline.ts)
    sim.display(expanded='both', solution=prefix+suffix[1:])
    
    # set to global and to save animation
    sim.simulate(loops=2, offline=True)
#     sim.play(output='video') # TODO: uncomment on linux desktop, show=False)
#     sim.save() # TODO: uncomment on linux desktop
    
    # move to start position
    startConf = next(iter(sim.path))
    
    print(startConf)
    sim.robot.move(startConf)
    
    while sim.step():
        pass
    return
    ############################################################################
    ### Execute on-line path planning algorithm ################################
    ############################################################################
    
    # compute potential for each state of PA
    with Timer('Computing potential function'):
        if not compute_potentials(sim.offline.checker):
            return
    
    # FIXME: HACK
    robot.controlspace = 0.1
    
    # initialize local on-line RRT planner
    sim.online = LocalPlanner(sim.offline.checker, sim.offline.ts, robot,
                              localSpec)
    
    # TODO: debug code, delete after use
    sim.online.sim = sim
    
    # define number of surveillance cycles to run
    cycles = 4
    # execute controller
    cycle = -1 # number of completed cycles, -1 accounts for the prefix 
    while cycle < cycles:
        # update the locally sensed requests and obstacles
        requests, obstacles = robot.sensor.sense()
        with Timer('local planning'):
            # feed data to planner and get next control input
            nextConf = sim.online.execute(requests, obstacles)
        
        sim.display(expanded=True, localinfo=('plan', 'trajectory'))
        
        # enforce movement
        robot.move(nextConf)
        # if completed cycle increment cycle
        if sim.update():
            cycle += 1
    
    ############################################################################
    ### Display the local transition systems and the on-line control policy ####
    ############################################################################
    
    # set to local and to save animation 
    sim.simulate(offline=False)
    sim.play(output='video', show=True)
#     sim.save() #TODO: uncomment on linux desktop


if __name__ == '__main__':
    np.random.seed(1002)
    caseStudy()