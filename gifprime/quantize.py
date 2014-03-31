"""Colour quantizer using "Adaptive Spatial Subdivision".

Implemented as described by ImageMagick:
http://www.imagemagick.org/script/quantize.php
"""

import itertools


# The maximum depth of the colour octree. Should be in range [3, 6]. Higher is
# slower but with higher quality.
# TODO: If < 8, even images with fewer than 256 colours will be quantized if
# colours are similar.
MAX_DEPTH = 8


class ColourCube(object):
    """A cube contained in a colour space."""

    def __init__(self, vertex_low, vertex_high, depth):
        self.vertex_low = vertex_low
        self.vertex_high = vertex_high
        self.children = None
        self.center = tuple([((self.vertex_low[i] + self.vertex_high[i]) / 2)
                             for i in range(3)])
        self.depth = depth
        self.num_pixels = 0
        self.num_pixels_exclusive = 0
        self.pixel_sums = (0, 0, 0)
        self.error = 0

    def get_children(self):
        """Return this cube's 8 child cubes, or [] if this is a leaf

        Children are lazily instantiated as needed.
        """
        if self.depth == MAX_DEPTH:
            self.children = []
        elif self.children is None:
            v = self.vertex_low
            perms = itertools.product([0, 1], repeat=3)
            size = (self.vertex_high[0] - self.vertex_low[0]) / 2
            child_lows = [tuple([v[i] + (size + 1) * p[i] for i in range(3)])
                          for p in perms]
            self.children = [
                ColourCube(low, (low[0] + size, low[1] + size, low[2] + size),
                           self.depth + 1)
                for low in child_lows
            ]
        return self.children

    def has_initialized_children(self):
        """Return True if this node's children have been initialized."""
        return self.children is not None and len(self.children) > 0

    def contains(self, colour):
        """Return True if this cube contains colour."""
        return all((colour[i] >= self.vertex_low[i] and
                    colour[i] <= self.vertex_high[i]) for i in range(3))

    def center_squared_distance_to(self, colour):
        """Return the squared distance from this cube's center to colour."""
        return abs(sum(pow(colour[i] - self.center[i], 2) for i in range(3)))

    def get_deepest_containing(self, colour):
        """Return the deepest node containing colour.

        Does not generate new nodes.
        """
        if self.has_initialized_children():
            for child in self.get_children():
                if child.contains(colour):
                    return child.get_deepest_containing(colour)
        return self

    def prune(self, child):
        """Prune the given child of this node."""
        if child not in self.get_children():
            raise ValueError('{} is not a child of {}'.format(child, self))
        # recursively prune the child's children
        # XXX child.children can be None here
        # iterate over copy of the list
        for child_child in list(child.get_children()):
            child.prune(child_child)
        assert child.children == [], 'child has not been recursively pruned'
        # prune the child
        self.num_pixels_exclusive += child.num_pixels_exclusive
        self.pixel_sums = tuple(self.pixel_sums[i] + child.pixel_sums[i]
                                for i in range(3))
        self.children.remove(child)

    def __repr__(self):
        return '<{} at {} to {}>'.format(self.__class__.__name__,
                                         self.vertex_low, self.vertex_high)


RGB = ColourCube((0, 0, 0), (255, 255, 255), 0)
TEST_IMG = [(255, 0, 0), (254, 0, 0), (100, 0, 0), (0, 0, 0)]

def all_nodes(node):
    """Return all initialized nodes."""
    nodes = [node]
    while nodes:
        node = nodes.pop()
        yield node
        if node.has_initialized_children():
            for child in node.get_children():
                nodes.append(child)


def quantize(rgb_tuples, max_colours):
    """Quantize list of RGB tuples to at most max_colours.

    Returns a colour table and a mapping from every unique colour to a colour
    table index.
    """
    tree = ColourCube((0, 0, 0), (255, 255, 255), 0)

    # CLASSIFICATION

    for pixel in rgb_tuples:
        node = tree
        while node is not None:
            # update the node
            node.num_pixels += 1
            if len(node.get_children()) == 0:
                node.num_pixels_exclusive += 1
                node.pixel_sums = tuple([node.pixel_sums[i] + pixel[i]
                                         for i in range(3)])
            node.error += node.center_squared_distance_to(pixel)

            # find the next node
            children = node.get_children()
            node = None
            for child in children:
                if child.contains(pixel):
                    node = child

    # REDUCTION

    # XXX remove unused nodes
    for node in all_nodes(tree):
        if node.has_initialized_children():
            for child in list(node.get_children()):
                if child.num_pixels == 0:
                    node.children.remove(child)

    min_e = 0
    while len(list(node for node in all_nodes(tree)
                   if node.num_pixels_exclusive > 0)) > max_colours:
        nodes = [tree]
        while nodes:
            node = nodes.pop()
            assert node.error > 0, str(node)
            children = node.get_children()
            for child in children:
                if child.error <= min_e:
                    # prune the nodes with the MINIMUM error
                    node.prune(child)
                else:
                    nodes.append(child)

        min_e = min(node.error for node in all_nodes(tree))

    # ASSIGNMENT

    colour_list = []
    node_to_index = {}
    nodes = [tree]
    while len(nodes) > 0:
        node = nodes.pop()
        if node.num_pixels_exclusive > 0:
            mean_col = tuple(node.pixel_sums[i] / node.num_pixels_exclusive
                             for i in range(3))
            colour_list.append(mean_col)
            node_to_index[node] = len(colour_list) - 1
        if node.has_initialized_children():
            for child in node.get_children():
                nodes.append(child)

    # for each pixel, find deepest code containing its colour
    colour_map = {}  # (r, g, b) -> index in colour table
    for pixel in rgb_tuples:
        if pixel not in colour_map:
            node = tree.get_deepest_containing(pixel)
            colour_map[pixel] = node_to_index[node]

    return colour_list, colour_map
