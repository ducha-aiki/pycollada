####################################################################
#                                                                  #
# THIS FILE IS PART OF THE pycollada LIBRARY SOURCE CODE.          #
# USE, DISTRIBUTION AND REPRODUCTION OF THIS LIBRARY SOURCE IS     #
# GOVERNED BY A BSD-STYLE SOURCE LICENSE INCLUDED WITH THIS SOURCE #
# IN 'COPYING'. PLEASE READ THESE TERMS BEFORE DISTRIBUTING.       #
#                                                                  #
# THE pycollada SOURCE CODE IS (C) COPYRIGHT 2011                  #
# by Jeff Terrace and contributors                                 #
#                                                                  #
####################################################################

"""This module contains utility functions"""

import numpy
import math

from collada.common import DaeMalformedError, E, tag


def falmostEqual(a, b, rtol=1.0000000000000001e-05, atol=1e-08):
    """Checks if the given floats are almost equal. Uses the algorithm
    from numpy.allclose.

    :param float a:
      First float to compare
    :param float b:
      Second float to compare
    :param float rtol:
      The relative tolerance parameter
    :param float atol:
      The absolute tolerance parameter

    :rtype: bool

    """

    return math.fabs(a - b) <= (atol + rtol * math.fabs(b))


def toUnitVec(vec):
    """Converts the given vector to a unit vector

    :param numpy.array vec:
      The vector to transform to unit length

    :rtype: numpy.array

    """
    return vec / numpy.sqrt(numpy.vdot(vec, vec))


def checkSource(source, components, maxindex):
    """Check if a source objects complies with the needed `components` and has the needed length

    :param collada.source.Source source:
      A source instance to check
    :param tuple components:
      A tuple describing the needed channels, e.g. ``('X','Y','Z')``
    :param int maxindex:
      The maximum index that refers to this source

    """
    if len(source.data) <= maxindex:
        raise DaeMalformedError(
            "Indexes (maxindex=%d) for source '%s' (len=%d) go beyond the limits of the source"
            % (maxindex, source.id, len(source.data)))

    # some files will write sources with no named parameters
    # by spec, these params should just be skipped, but we need to
    # adapt to the failed output of others...
    if len(source.components) == len(components):
        source.components = components

    if source.components != components:
        raise DaeMalformedError('Wrong format in source %s' % source.id)
    return source


def normalize_v3(arr):
    """Normalize a numpy array of 3 component vectors with shape (N,3)

    :param numpy.array arr:
      The numpy array to normalize

    :rtype: numpy.array

    """
    lens = numpy.sqrt(arr[:, 0]**2 + arr[:, 1]**2 + arr[:, 2]**2)
    lens[numpy.equal(lens, 0)] = 1
    arr[:, 0] /= lens
    arr[:, 1] /= lens
    arr[:, 2] /= lens
    return arr


def dot_v3(arr1, arr2):
    """Calculates the dot product for each vector in two arrays

    :param numpy.array arr1:
      The first array, shape Nx3
    :param numpy.array arr2:
      The second array, shape Nx3

    :rtype: numpy.array

    """
    return arr1[:, 0] * arr2[:, 0] + arr1[:, 1] * arr2[:, 1] + arr2[:, 2] * arr1[:, 2]


class LazyIndexedList:
    """
    A lazy-loading indexed list that stores XML nodes and loads objects on demand.
    This is useful for large COLLADA files where you may not need all objects.
    """

    def __init__(self, attrs, collada, loader_func, id_attr='id'):
        self._attrs = tuple(attrs)
        self._collada = collada
        self._loader_func = loader_func
        self._id_attr = id_attr
        self._pending_nodes = {}  # id -> xmlnode
        self._loaded = {}  # id -> loaded object
        self._loaded_objects = set()  # fast O(1) containment check for objects
        self._order = []  # maintain insertion order

    def add_node(self, xmlnode):
        """Add an XML node for lazy loading."""
        obj_id = xmlnode.get(self._id_attr)
        if obj_id:
            self._pending_nodes[obj_id] = xmlnode
            self._order.append(obj_id)

    def _load_item(self, obj_id):
        """Load and cache an item by id."""
        if obj_id in self._loaded:
            return self._loaded[obj_id]
        if obj_id in self._pending_nodes:
            node = self._pending_nodes.pop(obj_id)
            obj = self._loader_func(self._collada, {}, node)
            self._loaded[obj_id] = obj
            self._loaded_objects.add(id(obj))  # Track by id for fast containment
            return obj
        return None

    def _load_all(self):
        """Load all pending items."""
        for obj_id in list(self._pending_nodes.keys()):
            self._load_item(obj_id)

    def __getitem__(self, key):
        if isinstance(key, str):
            return self.get(key)
        # Numeric index - need to load item at that position
        if key < 0:
            key = len(self) + key
        if key < 0 or key >= len(self._order):
            raise IndexError("list index out of range")
        obj_id = self._order[key]
        return self._load_item(obj_id)

    def get(self, key, default=None):
        if key in self._loaded:
            return self._loaded[key]
        if key in self._pending_nodes:
            return self._load_item(key)
        return default

    def __len__(self):
        return len(self._order)

    def __iter__(self):
        for obj_id in self._order:
            yield self._load_item(obj_id)

    def __contains__(self, item):
        if isinstance(item, str):
            return item in self._loaded or item in self._pending_nodes
        # Fast O(1) check using object id
        return id(item) in self._loaded_objects

    def append(self, obj):
        """Append an already-loaded object."""
        for attr in self._attrs:
            key = getattr(obj, attr)
            self._loaded[key] = obj
            self._loaded_objects.add(id(obj))
            if key not in self._order:
                self._order.append(key)

    def extend(self, items):
        for item in items:
            self.append(item)


class IndexedList(list):
    """
    Class that combines a list and a dict into a single class
     - Written by Hugh Bothwell (http://stackoverflow.com/users/33258/hugh-bothwell)
     - Original source available at:
          http://stackoverflow.com/questions/5332841/python-list-dict-property-best-practice/5334686#5334686
     - Modifications by Jeff Terrace
    Given an object, obj, that has a property x, this allows you to create an IndexedList like so:
       L = IndexedList([], ('x'))
       o = obj()
       o.x = 'test'
       L.append(o)
       L[0] # = o
       L['test'] # = o
    """

    def __init__(self, items, attrs):
        super(IndexedList, self).__init__(items)
        # do indexing
        self._attrs = tuple(attrs)
        self._index = {}
        _add = self._addindex
        for obj in self:
            _add(obj)

    def _addindex(self, obj):
        _idx = self._index
        for attr in self._attrs:
            _idx[getattr(obj, attr)] = obj

    def _delindex(self, obj):
        _idx = self._index
        for attr in self._attrs:
            try:
                del _idx[getattr(obj, attr)]
            except KeyError:
                pass

    def __delitem__(self, ind):
        try:
            obj = list.__getitem__(self, ind)
        except (IndexError, TypeError):
            obj = self._index[ind]
            ind = list.index(self, obj)
        self._delindex(obj)
        return list.__delitem__(self, ind)

    def __delslice__(self, i, j):
        return list.__delslice__(self, i, j)

    def __getitem__(self, ind):
        try:
            return self._index[ind]
        except KeyError:
            if isinstance(ind, str):
                raise
            return list.__getitem__(self, ind)

    def get(self, key, default=None):
        try:
            return self._index[key]
        except KeyError:
            return default

    def __contains__(self, item):
        if item in self._index:
            return True
        return list.__contains__(self, item)

    def __getslice__(self, i, j):
        return IndexedList(list.__getslice__(self, i, j), self._attrs)

    def __setitem__(self, ind, new_obj):
        try:
            obj = list.__getitem__(self, ind)
        except (IndexError, TypeError):
            obj = self._index[ind]
            ind = list.index(self, obj)
        self._delindex(obj)
        self._addindex(new_obj)
        return list.__setitem__(ind, new_obj)

    def __setslice__(self, i, j, newItems):
        _get = self.__getitem__
        _add = self._addindex
        _del = self._delindex
        newItems = list(newItems)
        # remove indexing of items to remove
        for ind in range(i, j):
            _del(_get(ind))
        # add new indexing
        if isinstance(newItems, IndexedList):
            self._index.update(newItems._index)
        else:
            for obj in newItems:
                _add(obj)
        # replace items
        return list.__setslice__(self, i, j, newItems)

    def append(self, obj):
        self._addindex(obj)
        return list.append(self, obj)

    def extend(self, newList):
        newList = list(newList)
        if isinstance(newList, IndexedList):
            self._index.update(newList._index)
        else:
            _add = self._addindex
            for obj in newList:
                _add(obj)
        return list.extend(self, newList)

    def insert(self, ind, new_obj):
        # ensure that ind is a numeric index
        try:
            obj = list.__getitem__(self, ind)
        except (IndexError, TypeError):
            obj = self._index[ind]
            ind = list.index(self, obj)
        self._addindex(new_obj)
        return list.insert(self, ind, new_obj)

    def pop(self, ind=-1):
        # ensure that ind is a numeric index
        try:
            obj = list.__getitem__(self, ind)
        except (IndexError, TypeError):
            obj = self._index[ind]
            ind = list.index(self, obj)
        self._delindex(obj)
        return list.pop(self, ind)

    def remove(self, ind_or_obj):
        try:
            obj = self._index[ind_or_obj]
            ind = list.index(self, obj)
        except KeyError:
            ind = list.index(self, ind_or_obj)
            obj = list.__getitem__(self, ind)
        self._delindex(obj)
        return list.remove(self, ind)


def _correctValInNode(outernode, tagname, value):
    innernode = outernode.find(tag(tagname))
    if value is None and innernode is not None:
        outernode.remove(innernode)
    elif innernode is not None:
        innernode.text = str(value)
    elif value is not None:
        outernode.append(E(tagname, str(value)))
