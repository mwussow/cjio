"""Demonstrate what is when we define the CityModel-objects in a top-down approach

"""

from typing import List, Dict


class CityModel(object):
    """Equivalent to the main CityJSON object in the data model"""
    type = 'CityJSON'
    cityjson_version = '1.0'

    def __init__(self, cityobjects):
        self.cityobjects = cityobjects

    def get_cityobjects(self, type=None):
        """Return a generator over the CityObjects of the given type

        If type=None, return all CityObjects
        """
        if type is None:
            return self.cityobjects
        else:
            if not isinstance(type, str):
                raise TypeError("type parameter must be a string")
            target = type.lower()
            return (co for co in self.cityobjects if co.type.lower() == target)


class CityObject(object):
    """CityObject class"""
    def __init__(self, id, type, geometry):
        self.id = id
        self.type = type
        self.geometry = geometry


class SemanticSurface(object):
    """SemanticSurface class

    It doesn't store the coordinates as Geometry, just pointers to parts of the Geometry
    """
    def __init__(self, type, values, children=None, parent=None, attributes=None):
        self.type = type
        self.children = children
        self.parent = parent
        self.attributes = attributes
        self.surface_idx = values

    @property
    def surface_idx(self):
        return self._surface_idx

    @surface_idx.setter
    def surface_idx(self, values):
        self._surface_idx = self._index_surface_boundaries(values)

    @staticmethod
    def _index_surface_boundaries(values):
        """Create an index of the Surfaces which have semantic value in a Geometry boundary

        It creates a lookup table for the indicies to the Surfaces in a boundary that have semantics.
        The key of the lookup table are the indices of the SemanticSurface objects in the Geometry.surfaces array.
        The idea is that by using the index, the geometry of the Surface can be retrieved from
        the boundary in O(1) time, instead of looping through the 'semantics.values' and
        'boundaries' each time the geometry of a semantic surface needs to be retrieved.

        .. note:: Only works with MultiSurface or more complex boundaries

        :param values: The array of values from a Geometry Object's `semantics` member
        :return: A dict of indices to the surfaces in a boundary.
        """
        # TODO BD optimize: Again, here recursion seems to be like a nice alternative
        surface_idx = dict()
        if not values or len(values) == 0:
            return surface_idx
        else:
            for i, idx in enumerate(values):
                if idx is not None:
                    if isinstance(idx, list):
                        for j, jdx in enumerate(idx):
                            if jdx is not None:
                                if isinstance(jdx, list):
                                    for k, kdx in enumerate(jdx):
                                        if isinstance(kdx, list):
                                            raise TypeError("The 'values' member of 'semantics' is too many levels deep")
                                        if kdx is not None:
                                            if kdx not in surface_idx.keys():
                                                surface_idx[kdx] = [[i,j,k]]
                                            else:
                                                surface_idx[kdx].append([i,j,k])
                                else:
                                    if jdx not in surface_idx.keys():
                                        surface_idx[jdx] = [[i,j]]
                                    else:
                                        surface_idx[jdx].append([i,j])
                    else:
                        if idx not in surface_idx.keys():
                            surface_idx[idx] = [[i]]
                        else:
                            surface_idx[idx].append([i])
            return surface_idx


class Geometry(object):
    """CityJSON Geometry object"""
    def __init__(self, type: str=None, lod: int=None,
                 boundaries: List=None, semantics_obj: Dict=None,
                 vertices=None):
        self.type = type
        self.lod = lod
        self.boundaries = self._dereference_boundary(type, boundaries, vertices)
        self.surfaces = self._dereference_surfaces(semantics_obj)

    @staticmethod
    def _vertex_mapper(boundary, vertices):
        """Maps vertex coordinates to vertex indices"""
        # NOTE BD: it might be ok to simply return the iterator from map()
        return list(map(lambda x: vertices[x], boundary))

    @staticmethod
    def _get_surface_boundaries(boundaries, surface_idx):
        """Get the surface at the index location from the Geometry boundary

        .. note: Interior surfaces don't have semantics and they are returned with the
        exterior.

        :param boundaries: Geometry boundaries
        :param surface_idx: Surface index generated by :py:class: `m̀odels.SemanticSurface`
        :return: Surfaces from the boundary that correspond to the index.
        """
        # TODO BD: essentially, this function is meant to returns a MultiSurface,
        # which is a collection of surfaces that have semantics --> consider returning
        # a Geometry object of MultiSufrace type
        if not surface_idx or len(surface_idx) == 0:
            return []
        else:
            return [boundaries[i[0]] if len(i) == 1
                    else boundaries[i[0]][i[1]] if len(i) == 2
                    else boundaries[i[0]][i[1]][i[2]]
                    for i in surface_idx]

    def _dereference_boundary(self, btype, boundary, vertices):
        """Replace vertex indices with vertex coordinates in the geomery boundary"""
        # TODO BD optimize: would be much faster with recursion
        if not boundary:
            return list()
        if btype.lower() == 'multipoint':
            return self._vertex_mapper(boundary, vertices)
        elif btype.lower() == 'multilinestring':
            return [self._vertex_mapper(b, vertices) for b in boundary]
        elif btype.lower() == 'multisurface' or btype.lower() == 'compositesurface':
            s = list()
            for surface in boundary:
                s.append([self._vertex_mapper(b, vertices) for b in surface])
            return s
        elif btype.lower() == 'solid':
            sh = list()
            for shell in boundary:
                s = list()
                for surface in shell:
                    s.append([self._vertex_mapper(b, vertices) for b in surface])
                sh.append(s)
            return sh
        elif btype.lower() == 'multisolid' or btype.lower() == 'compositesolid':
            solids = list()
            for solid in boundary:
                sh = list()
                for shell in solid:
                    s = list()
                    for surface in shell:
                        s.append([self._vertex_mapper(b, vertices) for b in surface])
                    sh.append(s)
                solids.append(sh)
            return solids


    def _dereference_surfaces(self, semantics_obj):
        """Dereferene a semantic surface
        :param semantics_obj: Semantic Surface object as extracted from CityJSON file
        """
        semantic_surfaces = dict()
        if not semantics_obj or not semantics_obj['values']:
            return semantic_surfaces
        else:
            for i,srf in enumerate(semantics_obj['surfaces']):
                attributes = dict()
                for key,value in srf.items():
                    if key == 'type':
                        type = value
                    elif key == 'children':
                        children = value
                    elif key == 'parent':
                        parent = value
                    else:
                        attributes[key] = value
                # TODO B: link to geometry
                semantic_surfaces[i] = SemanticSurface(type=type,
                                                        children=children,
                                                        parent=parent,
                                                        attributes=attributes)
            return semantic_surfaces


    def get_surfaces(self, type=None, lod=None):
        """Get the specific surface of the model

        If the surface type is not provided, or semantic surfaces are not present (eg. LoD1), then the whole boundary
        is returned.
        """

    # @property
    # def semantics(self):
    #     """The Semantic Surface types in the Geometry"""
    #     return (s['type'] for s in self.semantics_obj['surfaces'])
