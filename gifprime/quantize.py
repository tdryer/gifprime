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

    def __init__(self, vertex_low, vertex_high, depth=0):
        self.vertex_low = vertex_low
        self.vertex_high = vertex_high
        self.children = []
        self.center = tuple([((self.vertex_low[i] + self.vertex_high[i]) / 2)
                             for i in range(3)])
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
        midpoints = [self.vertex_low[i] + size + 1 for i in range(3)]
        child_low = tuple(self.vertex_low[i] if colour[i] < midpoints[i]
                          else midpoints[i] for i in range(3))
        # if that cube has already been generated, use it
        for child in self.children:
            if child.vertex_low == child_low:
                return child
        # otherwise, instantiate a new ColourCube and add it as a child
        child_high = tuple(child_low[i] + size for i in range(3))
        child = ColourCube(child_low, child_high, self.depth + 1)
        self.children.append(child)
        assert len(self.children) <= 8
        assert child.contains(colour), (
            '{} does not contain {}'.format(child, colour))
        return child

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
        for child in self.children:
            if child.contains(colour):
                return child.get_deepest_containing(colour)
        return self

    def prune(self, child):
        """Prune the given child of this node."""
        assert child in self.children
        # recursively prune the child's children
        # XXX child.children can be None here
        # iterate over copy of the list since it will be mutated
        for child_child in list(child.children):
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


def all_nodes(node):
    """Return all initialized nodes."""
    nodes = [node]
    while nodes:
        node = nodes.pop()
        yield node
        for child in node.children:
            nodes.append(child)


def _classify(rgb_tuples):
    """Construct octree from colours in image."""
    tree = ColourCube((0, 0, 0), (255, 255, 255))
    for pixel in rgb_tuples:
        node = tree
        while node is not None:
            # update the node
            node.num_pixels += 1
            child = node.generate_child_for(pixel)
            if child is None:
                node.num_pixels_exclusive += 1
                node.pixel_sums = tuple([node.pixel_sums[i] + pixel[i]
                                         for i in range(3)])
            else:
                node.error += node.center_squared_distance_to(pixel)
            node = child
    return tree


def _reduce(tree, max_colours):
    """Reduce octree until it contains fewer than max_colours colours."""
    min_e = 0
    while len(list(node for node in all_nodes(tree)
                   if node.num_pixels_exclusive > 0)) > max_colours:
        nodes = [tree]
        while nodes:
            node = nodes.pop()
            assert node.error > 0, str(node)
            # iterate over COPY of the list
            for child in list(node.children):
                # prune the nodes with the MINIMUM error
                if child.error <= min_e:
                    node.prune(child)
                else:
                    nodes.append(child)

        # TODO get rid of the extra loop
        min_e = min(node.error for node in all_nodes(tree))


def _assign(rgb_tuples, tree):
    """Use octree to assign the image's colour to quantized colours."""
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
        for child in node.children:
            nodes.append(child)

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
