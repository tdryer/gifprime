import pygame
import sys

pygame.init()


class LazyFrames(object):
    """Lazy GIF image 'generator'."""

    def __init__(self, gif):
        self.gif = gif
        self.surfaces = {}
        self.current = None
        self.shown_count = 0

    def get_surface(self, i):
        """Gets the PyGame Surface corresponding to image[i] and its delay."""
        if i not in self.surfaces:
            image = self.gif.images[i]
            data = ''.join(''.join(chr(c) for c in pixel)
                           for pixel in image.rgba_data)
            self.surfaces[i] = pygame.image.fromstring(data, self.gif.size,
                                                       'RGBA')

        return self.surfaces[i], self.gif.images[i].delay_ms

    def has_next(self):
        """Returns True iff. there is a next frame."""
        if self.current is None or self.gif.loop_count == 0:
            return True
        else:
            num_loop = self.shown_count / len(self.gif.images)
            return not num_loop == self.gif.loop_count

    def next(self):
        """Returns the next (surface, delay)."""
        if self.current is None:
            self.current = -1

        self.shown_count += 1
        self.current = (self.current + 1) % len(self.gif.images)
        return self.get_surface(self.current)

    def has_prev(self):
        """Returns True iff. there is a previous frame."""
        if self.current is None or self.gif.loop_count == 0:
            return True
        else:
            num_loop = -self.shown_count / len(self.gif.images)
            return not num_loop == self.gif.loop_count

    def prev(self):
        """Returns the previous (surface, delay)."""
        if self.current is None:
            self.current = len(self.gif.images)

        self.shown_count -= 1
        self.current = (self.current - 1) % len(self.gif.images)
        return self.get_surface(self.current)


class GIFViewer(object):

    FORWARD = 'forward'
    BACKWARD = 'backward'
    PAUSED = 'pause'

    def __init__(self, gif, width=None, height=None, fps=60):
        self.gif = gif
        self.fps = fps

        self.state = self.FORWARD

        self.frames = LazyFrames(gif)
        self.frame_delay = 0
        self.ms_since_last_frame = 0

        # TODO: Automatically pick a good width/height
        self.width = self.gif.size[0] + 300
        self.height = self.gif.size[1] + 300

        # Setup pygame stuff
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.clock = pygame.time.Clock()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit(0)
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_LEFT:
                    self.state = self.BACKWARD
                    print 'Backward!'
                elif event.key == pygame.K_RIGHT:
                    self.state = self.FORWARD
                    print 'Forward!'
                elif event.key == pygame.K_SPACE:
                    self.state = self.PAUSED
                    print 'Paused!'

    def handle_draw(self, elapsed):
        if self.state != self.PAUSED:
            self.ms_since_last_frame += elapsed
            frame = None

            if self.ms_since_last_frame >= self.frame_delay:
                if self.state == self.FORWARD and self.frames.has_next():
                    frame, self.frame_delay = self.frames.next()
                    self.screen.blit(frame, (150, 150))
                elif self.state == self.BACKWARD and self.frames.has_prev():
                    frame, self.frame_delay = self.frames.prev()
                    self.screen.blit(frame, (150, 150))

            if frame is not None:
                self.ms_since_last_frame = 0

        pygame.display.flip()

    def show(self):
        now = 0

        while True:
            elapsed = pygame.time.get_ticks() - now
            now = pygame.time.get_ticks()

            self.handle_draw(elapsed)
            self.handle_events()
            self.clock.tick(self.fps)
