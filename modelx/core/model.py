# Copyright (c) 2017 Fumito Hamamura <fumito.ham@gmail.com>

# This library is free software: you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library.  If not, see <http://www.gnu.org/licenses/>.

from textwrap import dedent
import pickle

import networkx as nx

from modelx.core.base import Impl, LazyEvalDict, LazyEvalChainMap
from modelx.core.cells import CellArgs
from modelx.core.space import SpaceContainerImpl, SpaceContainer
from modelx.core.util import is_valid_name


class DependencyGraph(nx.DiGraph):
    """Directed Graph of ObjectArgs"""

    def clear_descendants(self, source, clear_source=True):
        """Remove all descendants of(reachable from) `source`.

        Args:
            source: Node descendants
            clear_source(bool): Remove origin too if True.
        Returns:
            set: The removed nodes.
        """
        desc = nx.descendants(self, source)
        if clear_source:
            desc.add(source)
        self.remove_nodes_from(desc)
        return desc

    def clear_obj(self, obj):
        """"Remove all nodes with `obj` and their descendants."""
        obj_nodes = self.get_nodes_with(obj)
        removed = set()
        for node in obj_nodes:
            if self.has_node(node):
                removed.update(self.clear_descendants(node))
        return removed

    def get_nodes_with(self, obj):
        """Return nodes with `obj`."""
        result = set()
        for node in nx.nodes_iter(self):
            if node.obj_ == obj:
                result.add(node)
        return result

class ModelImpl(SpaceContainerImpl):

    def __init__(self, *, system, name):
        SpaceContainerImpl.__init__(self, system, if_class=Model,
                                    paramfunc=None)

        self.cellgraph = DependencyGraph()
        self.currentspace = None

        if not name:
            self.name = system._modelnamer.get_next(system.models)
        elif is_valid_name(name):
            self.name = name
        else:
            raise ValueError("Invalid name '%s'." % name)

        Impl.__init__(self, Model)

        self._global_refs = LazyEvalDict(data={'__builtins__': __builtins__})
        self._spaces = LazyEvalDict()
        self._namespace = LazyEvalChainMap([self._spaces, self._global_refs])

    def clear_descendants(self, source, clear_source=True):
        """Clear values and nodes calculated from `source`."""
        removed = self.cellgraph.clear_descendants(source, clear_source)
        for cell in removed:
            del cell.cells.data[cell.argvalues]

    def clear_obj(self, obj):
        """Clear values and nodes of `obj` and their dependants."""
        removed = self.cellgraph.clear_obj(obj)
        for cell in removed:
            del cell.cells.data[cell.argvalues]

    @property
    def repr_(self):
        format_ = dedent("""\
        name: %s
        spaces(%s): %s""")

        return format_ % (
            self.name,
            len(self.spaces), list(self.spaces.keys()))

    @property
    def model(self):
        return self

    @property
    def global_refs(self):
        return self._global_refs.update_data()

    @property
    def namespace(self):
        return self._namespace.update_data()

    def close(self):
        self.system.close_model(self)

    def save(self, filepath):
        with open(filepath, 'wb') as file:
            pickle.dump(self.interface, file, protocol=4)

    def get_object(self, name):
        """Retrieve an object by a dotted name relative to the model."""
        parts = name.split('.')
        space = self.spaces[parts.pop(0)]
        if parts:
            return space.get_object('.'.join(parts))
        else:
            return space

    # ----------------------------------------------------------------------
    # Serialization by pickle

    state_attrs = ['name',
                   'cellgraph',
                   '_global_refs'] + SpaceContainerImpl.state_attrs

    def __getstate__(self):

        state = {key: value for key, value in self.__dict__.items()
                 if key in self.state_attrs}

        # state['_global_refs'] = self._global_refs.data.copy()

        mapping = {}
        for node in self.cellgraph:
            name = node.obj_.get_fullname(omit_model=True)
            mapping[node] = (name, node.argvalues)

        state['cellgraph'] = nx.relabel_nodes(self.cellgraph, mapping)

        return state

    def __setstate__(self, state):
        # state['_global_refs']['__builtins__'] = __builtins__
        self.__dict__.update(state)

    def restore_state(self, system):
        """Called after unpickling to restore some attributes manually."""
        SpaceContainerImpl.restore_state(self, system)
        mapping = {}
        for node in self.cellgraph:
            name, argvalues = node
            cells = self.get_object(name)
            mapping[node] = CellArgs(cells, argvalues)

        self.cellgraph = nx.relabel_nodes(self.cellgraph, mapping)

    def del_space(self, name):
        del self.spaces[name]
        self.spaces.set_update()

    def _set_space(self, space):

        if space.name in self.spaces:
            self.del_space(space.name)
        elif space.name in self.global_refs:
            raise KeyError("Name '%s' already already assigned" % self.name)

        self.spaces[space.name] = space
        self.spaces.set_update()

    def del_ref(self, name):
        del self.global_refs[name]
        self.global_refs.set_update()

    def get_attr(self, name):
        if name in self.spaces:
            return self.spaces[name].interface
        elif name in self.global_refs:
            return self.global_refs[name]
        else:
            raise KeyError("Model '{0}' does not have '{1}'".\
                           format(self.name, name))

    def set_attr(self, name, value):
        if name in self.spaces:
            raise KeyError("Space named '%s' already exist" % self.name)

        self.global_refs[name] = value
        self.global_refs.set_update()

    def del_attr(self, name):

        if name in self.spaces:
            self.del_space(name)
        elif name in self.global_refs:
            self.del_ref(name)
        else:
            raise KeyError("Name '%s' not defined" % name)


class Model(SpaceContainer):
    """Unit of work that contains spaces.

    A model is a unit of work. It can be saved to a file and loaded again.
    A model contains spaces.
    """

    @property
    def currentspace(self):
        """The current space of the model."""
        return self._impl.currentspace.interface

    def save(self, filepath):
        """Save the model to a file."""
        self._impl.save(filepath)

    def close(self):
        """Close the model."""
        self._impl.close()

    # ----------------------------------------------------------------------
    # Getting and setting attributes

    def __getattr__(self, name):
        return self._impl.get_attr(name)

    def __setattr__(self, name, value):
        self._impl.set_attr(name, value)

    def __delattr__(self, name):
        self._impl.del_attr(name)

    @property
    def cellgraph(self):
        """A directed graph of cells."""
        return self._impl.cellgraph

    def cur_space(self, name=None):
        """Set the current space to Space ``name`` and return it.

        If called without arguments, the current space is returned.
        Otherwise, the current space is set to the space named ``name``
        and the space is returned.
        """
        if name is None:
            return self._impl.currentspace.interface
        else:
            self._impl.currentspace = self._impl.spaces[name]
            return self.cur_space()




