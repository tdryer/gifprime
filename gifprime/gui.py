import itertools
import sys

import pygame

from gifprime.__main__ import GIF

pygame.init()


class GIFViewer(object):
    FPS = 1

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        self.clock = pygame.time.Clock()

        self.gif = GIF(sys.argv[1])

        self.surfaces = [pygame.image.fromstring(''.join(''.join(chr(c) for c in pixel)
                                                         for pixel in image.rgba_data),
                                                 self.gif.size, 'RGBA')
                         for image in self.gif.images]
        self.surfaces_iter = itertools.cycle(self.surfaces)

    def __do_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit(0)

    def __do_draw(self, elapsed):
        self.screen.blit(next(self.surfaces_iter), (0, 0))
        pygame.display.flip()

    def main(self):
        now = 0
        show_fps = 0
        while True:
            elapsed = pygame.time.get_ticks() - now
            now = pygame.time.get_ticks()
            self.__do_draw(elapsed)
            self.__do_events()
            self.clock.tick(self.FPS)
            show_fps = show_fps + 1
            if (show_fps % self.FPS == 0):
                print self.clock.get_fps()

if __name__ == '__main__':
    viewer = GIFViewer(300, 300)
    viewer.main()
