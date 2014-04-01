"""Colour quantizer using "Adaptive Spatial Subdivision".

Implemented as described by ImageMagick:
http://www.imagemagick.org/script/quantize.php
"""

import itertools


# The maximum depth of the colour octree. Should be in range [3, 6]. Higher is
# slower but with higher quality. Anything less than 8 will cause loss on
# images even with fewer than max_colours.
MAX_DEPTH = 8


# Minor optimization
COMPONENTS = range(3)


class ColourCube(object):
    """A cube contained in a colour space."""

    def __init__(self, vertex_low, vertex_high, depth=0):
        self.vertex_low = vertex_low
        self.vertex_high = vertex_high
        self.children = []
        self.center = tuple([((self.vertex_low[i] + self.vertex_high[i]) / 2)
                             for i in COMPONENTS])
        self.depth = depth
        self.num_pixels = 0
        self.num_pixels_exclusive = 0
        self.pixel_sums = (0, 0, 0)
        self.error = 0

    def generate_child_for(self, colour):
        """Return this Cube's child containing colour.

        Returns None if no such child exists. This method allows lazily
        generating the octree.
        """
        # if at max depth, there is no child
        if self.depth == MAX_DEPTH:
            return None
        # find the child cube that the colour falls in
        size = (self.vertex_high[0] - self.vertex_low[0]) / 2
        midpoints = [self.vertex_low[i] + size + 1 for i in COMPONENTS]
        child_low = tuple(self.vertex_low[i] if colour[i] < midpoints[i]
                          else midpoints[i] for i in COMPONENTS)
        # if that cube has already been generated, use it
        for child in self.children:
            if child.vertex_low == child_low:
                return child
        # otherwise, instantiate a new ColourCube and add it as a child
        child_high = tuple(child_low[i] + size for i in COMPONENTS)
        child = ColourCube(child_low, child_high, self.depth + 1)
        self.children.append(child)
        assert len(self.children) <= 8
        return child

    def contains(self, colour):
        """Return True if this cube contains colour."""
        return all((colour[i] >= self.vertex_low[i] and
                    colour[i] <= self.vertex_high[i]) for i in COMPONENTS)

    def center_squared_distance_to(self, colour):
        """Return the squared distance from this cube's center to colour."""
        return abs(sum(pow(colour[i] - self.center[i], 2) for i in COMPONENTS))

    def get_deepest_containing(self, colour):
        """Return the deepest node containing colour.

        Does not generate new nodes.
        """
        for child in self.children:
            if child.contains(colour):
                return child.get_deepest_containing(colour)
        return self

    def prune(self, child):
        """Prune the given child of this node."""
        assert child in self.children
        # recursively prune the child's children
        # iterate over copy of the list since it will be mutated
        for child_child in list(child.children):
            child.prune(child_child)
        assert child.children == [], 'child has not been recursively pruned'
        # prune the child
        self.num_pixels_exclusive += child.num_pixels_exclusive
        self.pixel_sums = tuple(self.pixel_sums[i] + child.pixel_sums[i]
                                for i in COMPONENTS)
        self.children.remove(child)

    def __repr__(self):
        return '<{} at {} to {}>'.format(self.__class__.__name__,
                                         self.vertex_low, self.vertex_high)


def all_nodes(node):
    """Yield all nodes via breadth-first search."""
    node_list = [node]
    while node_list:
        node = node_list.pop()
        node_list.extend(node.children)
        yield node

def _classify(rgb_tuples):
    """Construct octree from colours in image."""
    tree = ColourCube((0, 0, 0), (255, 255, 255))
    for pixel in rgb_tuples:
        node = tree
        while node is not None:
            # update the node
            node.num_pixels += 1
            child = node.generate_child_for(pixel)
            node.error += node.center_squared_distance_to(pixel)
            if child is None:
                node.num_pixels_exclusive += 1
                node.pixel_sums = tuple(node.pixel_sums[i] + pixel[i]
                                        for i in COMPONENTS)
            node = child
    return tree


def _reduce(tree, max_colours):
    """Reduce octree until it contains fewer than max_colours colours."""
    # do an initial count of the number of colours to find out if we need to
    # reduce at all
    num_colours = len(list(node for node in all_nodes(tree)
                           if node.num_pixels_exclusive > 0))
    min_e = 0
    # continue reducing until the number of colours is low enough
    while num_colours > max_colours:
        num_colours = 0
        next_min_e = None
        nodes = [tree]
        while nodes:
            node = nodes.pop()
            next_min_e = (node.error
                          if next_min_e is None or node.error < next_min_e
                          else next_min_e)
            assert node.error > 0
            # iterate over COPY of the list
            for child in list(node.children):
                # prune the nodes with the MINIMUM error
                if child.error <= min_e:
                    node.prune(child)
                else:
                    nodes.append(child)
            if node.num_pixels_exclusive > 0:
                num_colours += 1
        min_e = next_min_e


def _assign(rgb_tuples, tree):
    """Use octree to assign the image's colour to quantized colours."""
    colour_list = []
    node_to_index = {}
    for node in all_nodes(tree):
        if node.num_pixels_exclusive > 0:
            mean_col = tuple(node.pixel_sums[i] / node.num_pixels_exclusive
                             for i in COMPONENTS)
            colour_list.append(mean_col)
            node_to_index[node] = len(colour_list) - 1

    # for each pixel, find deepest code containing its colour
    colour_map = {}  # (r, g, b) -> index in colour table
    for pixel in rgb_tuples:
        if pixel not in colour_map:
            node = tree.get_deepest_containing(pixel)
            colour_map[pixel] = node_to_index[node]

    return colour_list, colour_map


def quantize(rgb_tuples, max_colours):
    """Quantize list of RGB tuples to at most max_colours.

    Returns a colour table and a mapping from every unique colour to a colour
    table index.
    """
    tree = _classify(rgb_tuples)
    _reduce(tree, max_colours)
    return _assign(rgb_tuples, tree)
