'''
Package defining finite abstraction models.

.. moduleauthor:: Cristian Ioan Vasile <cvasile@bu.edu>
'''
'''
    Package defining finite abstraction models.
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

from algorithms import *
from model import Model, model_representer, model_constructor
from ts import TS
from lomap import Buchi
from product import IncrementalProduct

# register yaml representers
try: # try using the libyaml if installed
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError: # else use default PyYAML loader and dumper
    from yaml import Loader, Dumper

Dumper.add_representer(Model, model_representer)
Dumper.add_representer(TS, model_representer)

Loader.add_constructor(Model.yaml_tag,
    lambda loader, model: model_constructor(loader, model, Model))
Loader.add_constructor(TS.yaml_tag,
    lambda loader, model: model_constructor(loader, model, TS))
