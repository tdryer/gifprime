import itertools
import sys

import pygame

from gifprime.__main__ import GIF

pygame.init()


class LazyFrames(object):
    """Lazy GIF image 'generator'."""

    def __init__(self, gif):
        self.gif = gif
        self.surfaces = {}
        self.current = None

    def __iter__(self):
        while True:
            yield self.next()

    def __reversed__(self):
        while True:
            yield self.prev()

    def get_surface(self, i):
        """Gets the PyGame Surface corresponding to image[i] and its delay."""
        if i not in self.surfaces:
            image = self.gif.images[i]
            data = ''.join(''.join(chr(c) for c in pixel)
                           for pixel in image.rgba_data)
            self.surfaces[i] = pygame.image.fromstring(data, gif.size, 'RGBA')

        return self.surfaces[i], self.gif.images[i].delay_ms

    def next(self):
        """Returns the next (surface, delay)."""
        if self.current is None:
            self.current = -1

        self.current = (self.current + 1) % len(self.gif.images)
        return self.get_surface(self.current)

    def prev(self):
        """Returns the previous (surface, delay)."""
        if self.current is None:
            self.current = len(self.gif.images)

        self.current = (self.current - 1) % len(self.gif.images)
        return self.get_surface(self.current)


class GIFViewer(object):

    def __init__(self, gif, width=None, height=None, fps=60):
        self.gif = gif
        self.fps = fps

        self.frames = LazyFrames(gif)
        self.frames_iter = iter(self.frames)
        self.frame_delay = 0
        self.ms_since_last_frame = 0

        # TODO: Automatically pick a good width/height
        self.width = 300
        self.height = 300

        # Setup pygame stuff
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.clock = pygame.time.Clock()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit(0)

    def handle_draw(self, elapsed):
        self.ms_since_last_frame += elapsed

        if self.ms_since_last_frame >= self.frame_delay:
            frame, self.frame_delay = next(self.frames_iter)
            self.ms_since_last_frame = 0
            self.screen.blit(frame, (0, 0))

        pygame.display.flip()

    def show(self):
        now = 0
        show_fps = 0

        while True:
            elapsed = pygame.time.get_ticks() - now
            now = pygame.time.get_ticks()

            self.handle_draw(elapsed)
            self.handle_events()
            self.clock.tick(self.fps)

            show_fps = show_fps + 1
            if show_fps % self.fps == 0:
                print self.clock.get_fps()


if __name__ == '__main__':
    gif = GIF(sys.argv[1])
    viewer = GIFViewer(gif, fps=60)
    viewer.show()
