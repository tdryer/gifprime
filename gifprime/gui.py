from sys import exit
import pygame

pygame.init()


class GIFViewer(object):
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        self.clock = pygame.time.Clock()

    def __do_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                exit(0)

    def __do_draw(self, elapsed):
        pygame.display.flip()

    def main(self):
        now = 0
        show_fps = 0
        while True:
            elapsed = pygame.time.get_ticks() - now
            now = pygame.time.get_ticks()
            self.__do_draw(elapsed)
            self.__do_events()
            self.clock.tick(60)
            show_fps = show_fps + 1
            if (show_fps % 60 == 0):
                print self.clock.get_fps()

if __name__ == '__main__':
    viewer = GIFViewer(300, 300)
    viewer.main()
