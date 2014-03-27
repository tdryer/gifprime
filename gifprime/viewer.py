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

    # minimum size that the window will open at
    MIN_SIZE = (256, 256)

    FORWARD = 'forward'
    BACKWARD = 'backward'
    PAUSED = 'pause'

    def __init__(self, gif, fps=60):
        self.gif = gif
        self.fps = fps

        self.state = self.FORWARD

        self.frames = LazyFrames(gif)
        self.frame_delay = 0
        self.current_frame = None
        self.ms_since_last_frame = 0

        # Set window size to minimum or large enough to show the gif
        self.size = (max(self.MIN_SIZE[0], self.gif.size[0]),
                     max(self.MIN_SIZE[1], self.gif.size[1]))

        # Setup pygame stuff
        pygame.display.set_caption('{} - gifprime'.format(gif.filename))
        self.set_screen()
        self.clock = pygame.time.Clock()

    def set_screen(self):
        """Set the video mode and self.screen.

        Called on init or when the window is resized.
        """
        self.screen = pygame.display.set_mode(self.size, pygame.RESIZABLE)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit(0)
            elif event.type == pygame.VIDEORESIZE:
                self.size = event.size
                # Reset the video mode so we can draw to a larger window
                self.set_screen()
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_ESCAPE:
                    sys.exit(0)
                elif event.key == pygame.K_LEFT:
                    self.state = self.BACKWARD
                    print 'Backward!'
                elif event.key == pygame.K_RIGHT:
                    self.state = self.FORWARD
                    print 'Forward!'
                elif event.key == pygame.K_SPACE:
                    self.state = self.PAUSED
                    print 'Paused!'

    def update(self, elapsed):
        """Update the animation state."""
        if self.state != self.PAUSED:
            self.ms_since_last_frame += elapsed
            frame = None
            if self.ms_since_last_frame >= self.frame_delay:
                if self.state == self.FORWARD and self.frames.has_next():
                    self.current_frame, self.frame_delay = self.frames.next()
                    self.ms_since_last_frame = 0
                elif self.state == self.BACKWARD and self.frames.has_prev():
                    self.current_frame, self.frame_delay = self.frames.prev()
                    self.ms_since_last_frame = 0

    def draw(self):
        """Draw the current animation state."""
        # position to draw frame so it is centered
        frame_pos = (self.size[0] / 2 - self.gif.size[0] / 2,
                     self.size[1] / 2 - self.gif.size[1] / 2)
        self.screen.blit(self.current_frame, frame_pos)
        pygame.display.flip()

    def show(self):
        now = 0

        while True:
            elapsed = pygame.time.get_ticks() - now
            now = pygame.time.get_ticks()

            self.update(elapsed)
            self.draw()
            self.handle_events()
            self.clock.tick(self.fps)
