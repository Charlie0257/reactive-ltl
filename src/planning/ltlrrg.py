'''
.. module:: ltlrrg
   :synopsis: The module implements the RRG based path planner with LTL constraints.
    The algorithm represents the (off-line) global component of the proposed
    framework.

.. moduleauthor:: Cristian Ioan Vasile <cvasile@bu.edu>
'''

'''
    The module implements the RRG based path planner with LTL constraints.
    The algorithm represents the (off-line) global component of the proposed
    framework.
    Copyright (C) 2014  Cristian Ioan Vasile <cvasile@bu.edu>
    Hybrid and Networked Systems (HyNeSs) Laboratory, Boston University

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

from collections import deque
from itertools import ifilter, imap, tee


from models import TS


class RRGPlanner(object):
    '''
    Class implementing the RRG based path planner with LTL constraints.
    The algorithm represents the (off-line) global component of the proposed
    framework.
    Planning is performed in the configuration space of the robot. However, this
    is transparent for this class and all calls to the underlying spaces
    (workspace and configuration) are wrapped as methods of the robot class.
    Thus the planner does not need to know how the samples are generated or
    mapped between the two spaces.
    '''
    
    def __init__(self, robot, checker, nn, iterations):
        '''Constructor'''
        self.name = 'RRG-based LTL path planner'
        self.maxIterations = iterations
        self.iteration = 0
        
        self.robot = robot
        symbols = self.robot.getSymbols(robot.initConf)
        
        # initialize transition system
        self.ts = TS(nnAlgorithm=nn)
        self.ts.addState(robot.initConf, symbols, init=True)
        
        # initialize checker
        self.checker = checker
        self.checker.addInitialState(robot.initConf, symbols)
        
        # TODO: initialize properly from mission parameters
#        self.eta = [0, float('inf')]
#        self.eta = [0.75, 2]
#        self.eta = [0.75, 1.8] # for dim 20
#         self.eta = [0.5, 1.25] # for dim 10
#         self.eta = [0.25, 0.7] # for dim 2
        self.eta = [0.5, 1.0] # for dim 2

    def solve(self):
        '''Try to solve the problem.'''
        for self.iteration in range(1, self.maxIterations+1):
            if self.iterate():
                return True
        return False
    
    def iterate(self):
        '''Execute one step of the off-line global planner.'''
#         import numpy #TODO: delete
        
        if not self.checker.foundPolicy():
            # update eta parameter # TODO: test
#            new_eta = (self.parent.world.getArea()/(2*pi*self.ts.g.number_of_nodes()))
#            self.eta = min(new_eta, self.eta)
#             print 'Eta:', self.eta
            
            # First phase - Forward
            # initialize update sets
            Q, Delta, E = dict(), set(), set()
            # sample new configuration
            randomConf = self.robot.sample()
            nearestState = self.nearest(randomConf)
            # steer towards the random configuration
            newConf = self.robot.steer(nearestState, randomConf)
            # set propositions
            newProp = self.robot.getSymbols(newConf)
#             if self.ts.g.number_of_nodes() == 32:
#                 lfar = list(self.far(newConf))
#                 if lfar:
#                     dfar = min([self.robot.cspace.dist(newConf, x) for x in lfar])
#                 else:
#                     dfar = float('inf')
#                 dts = min([self.robot.cspace.dist(newConf, x) for x in self.ts.g.nodes_iter()])
#                 if self.ts.g.number_of_edges() > 0:
#                     pts = min(map(lambda e: self.robot.cspace.dist(e[0], e[1]), self.ts.g.edges_iter()))
#                 else:
#                     pts = float('inf')
#                 print '-------->', newConf.coords, pts, dts, dfar, lfar
            
            k=0
            for state in self.far(newConf):
                k += 1
#                 # steer towards the random configuration
#                 newConf = self.robot.steer(state, randomConf)
#                 # set propositions
#                 newProp = self.robot.getSymbols(newConf)
                # check if the new state satisfies the global specification
#                 print 'simple', state.coords, newConf.coords, self.robot.isSimpleSegment(state, newConf)
                if self.robot.isSimpleSegment(state, newConf):
                    Ep = self.checker.check(self.ts, state, newConf, newProp,
                                            forward=True)
                    if Ep:
                        if newConf not in Q:
                            Q[newConf] = {'propositions': newProp}
                        Delta.add((state, newConf))
                        E.update(Ep)
            
            self.ts.addStates(Q.iteritems())
            self.ts.addTransitions(Delta)
            self.checker.update(E)
#             
#             if self.ts.g.number_of_nodes() == 33:
#                 print Q
#                 print self.iteration
#                 print 'begin forward'
#                 print k
#                 print 'Delta:', Delta
#                 print 'E:', E
#                 print 'Q:', Q
#                 print
#                 print '-------->', 'newconf:', newConf.coords, 'min-ts-dist:', pts, 'min-newconf-2-ts-dist:', dts, 'min-newconf-2-far-dist:', dfar, 'far(newconf):', lfar
#                 print 
#                 print 'end forward'
            
            
            # Second phase - Backward
            Delta = set()
            E = set()
            for newState, _ in Q.iteritems(): # for all newly added states
                for state in self.near(newState):
                    st = self.robot.steer(newState, state, atol=1e-8)
#                     if self.ts.g.number_of_nodes() == 33:
#                         print 'backward-steer:', 'newState:', newState.coords, 'stateTS:', state.coords, 'steerState:', st.coords, 'eq:', state == st, 'simple:', self.robot.isSimpleSegment(newState, state)
#                         print 'backward-steer:', 'coords-eq:', state.coords == st.coords, 'coords-diff:', state.coords - st.coords, 'state-eq', state == st
                    # if the robot can steer from a new state to another state
                    if (state == st) and \
                                    self.robot.isSimpleSegment(newState, state):
                        # check if the new state satisfies the global
                        # specification
                        Ep = self.checker.check(self.ts, newState, state,
                                                self.ts.g.node[state]['prop'],
                                                forward=False)
                        if Ep:
                            Delta.add((newState, state))
                            E.update(Ep)
            
#             if self.ts.g.number_of_nodes() == 33:
#                 print 'Delta:', Delta
#                 print E
            
            self.ts.addTransitions(Delta)
            self.checker.update(E)
            
#             print 'Size of PA:', self.checker.size()
#             print 'PA'
#             for u, d in self.checker.g.nodes_iter(data=True):
#                 print (u[0].coords, u[1]), d
#             for u, v in self.checker.g.edges_iter():
#                 print [(u[0].coords, u[1]), (v[0].coords, v[1])]
#             print 'Size of TS:', self.ts.size()
#             print 'TS'
#             for u, d in self.ts.g.nodes_iter(data=True):
#                 print u.coords, d
#             for u, v in self.ts.g.edges_iter():
#                 print (u.coords, v.coords)
#             print
            
            assert all([self.checker.buchi.g.has_edge(u[1], v[1]) for u, v in self.checker.g.edges_iter()]), '{} {}'.format(self.iteration, [((u[0].coords, u[1]), (v[0].coords, v[1])) for u, v in self.checker.g.edges_iter() if not self.checker.buchi.g.has_edge(u[1], v[1])])
            
            return self.checker.foundPolicy()
        
        return True
    
    def nearest(self, p):
        '''Returns the nearest configuration in the transition system.'''
        dist = self.robot.cspace.dist
#         print '[nearest]', p #TODO: delete this
#         print '[nearest]'
#         for node, data in self.ts.g.nodes_iter(data=True):
#             print node, data
#             print dist(p, node)
#         print '@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@'
#         print
#         print
#         print '@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@'
#         print
        return min(self.ts.g.nodes_iter(), key=lambda x: dist(p, x))
    
    def far(self, p):
        '''
        Return all states in the transition system that fall at distance d,
        d < self.eta[1], away from the given configuration p. If there is a
        state which is closer to the given configuration p than self.eta[0]
        then the function returns an empty list.
        '''
#         p = p.coords
        metric = self.robot.cspace.dist
        
#         dd = [metric(v, p) for v in self.ts.g.nodes_iter()]
#         print '[far]', dd, [d < self.eta[1] for d in dd]
#         
#         tt = list(ifilter(lambda v: metric(v, p) < self.eta[1], self.ts.g.nodes_iter()))
#         print '[far]', tt, map(lambda v: metric(v, p) <= self.eta[0], tt), any(map(lambda v: metric(v, p) <= self.eta[0], tt))
        
        ret, test = tee(ifilter(lambda v: metric(v, p) < self.eta[1],
                                self.ts.g.nodes_iter()))
        if any(imap(lambda v: metric(v, p) <= self.eta[0], test)):
            return iter([])
        return ret
    
    def near(self, p):
        '''
        Return all states in the transition system that fall at distance d,
        0 < d < self.eta[1], away from the given configuration p.
        '''    
#         p = p.coords
        metric = self.robot.cspace.dist
        return ifilter(lambda v: 0 < metric(v, p) < self.eta[1],
                       self.ts.g.nodes_iter())

if __name__ == '__main__':
    import doctest
    doctest.testmod()
