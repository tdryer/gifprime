"""Graphical user interface for viewing GIF animations."""

import pygame


pygame.init()
pygame.font.init()


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
    """Graphical GIF animation viewer."""

    # minimum size that the window will open at
    MIN_SIZE = (256, 256)

    def __init__(self, gif, fps=60):
        self.gif = gif
        self.fps = fps

        self.is_playing = True
        self.is_reversed = False
        self.is_scaled = False
        self.is_exiting = False
        self.is_showing_info = False

        self.bg_surface = pygame.image.load('background.png')
        self.font = pygame.font.Font(pygame.font.get_default_font(), 14)
        self.frames = LazyFrames(gif)
        self.frame_delay = 0
        self.current_frame = None
        self.ms_since_last_frame = 0
        self.info_lines = None

        # Set window size to minimum or large enough to show the gif
        self.size = (max(self.MIN_SIZE[0], self.gif.size[0]),
                     max(self.MIN_SIZE[1], self.gif.size[1]))

        # Setup pygame stuff
        filename = gif.filename.split('/')[-1]
        pygame.display.set_caption('{} - gifprime'.format(filename))
        self.screen = None
        self.set_screen()
        self.clock = pygame.time.Clock()

    def set_screen(self):
        """Set the video mode and self.screen.

        Called on init or when the window is resized.
        """
        self.screen = pygame.display.set_mode(self.size, pygame.RESIZABLE)

    def show_next_frame(self, backwards=False):
        """Switch to the next frame, or do nothing if there isn't one."""
        if not backwards and self.frames.has_next():
            self.current_frame, self.frame_delay = self.frames.next()
            self.ms_since_last_frame = 0
        elif backwards and self.frames.has_prev():
            self.current_frame, self.frame_delay = self.frames.prev()
            self.ms_since_last_frame = 0

    def handle_events(self):
        """Poll and handle pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_exiting = True
            elif event.type == pygame.VIDEORESIZE:
                self.size = event.size
                # Reset the video mode so we can draw to a larger window
                self.set_screen()
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_ESCAPE:
                    self.is_exiting = True
                elif event.key == pygame.K_LEFT:
                    # skip back one frame
                    self.show_next_frame(backwards=True)
                elif event.key == pygame.K_RIGHT:
                    # skip forward one frame
                    self.show_next_frame()
                elif event.key == pygame.K_SPACE:
                    # toggle playback
                    self.is_playing = not self.is_playing
                elif event.key == pygame.K_r:
                    # reverse playback direction
                    self.is_reversed = not self.is_reversed
                elif event.key == pygame.K_s:
                    # toggle scale to fit
                    self.is_scaled = not self.is_scaled
                elif event.key == pygame.K_i:
                    # toggle showing info
                    self.is_showing_info = not self.is_showing_info

    def update(self, elapsed):
        """Update the animation state."""
        if self.is_playing:
            self.ms_since_last_frame += elapsed
            if self.ms_since_last_frame >= self.frame_delay:
                self.show_next_frame(backwards=self.is_reversed)

        self.info_lines = [
            '{} {} {}'.format('Playing' if self.is_playing else 'Paused',
                              '(reversed)' if self.is_reversed else '',
                              '(rescaled)' if self.is_scaled else ''),
            'number of frames: {}'.format(len(self.gif.images)),
            'number of loops: {}'.format(
                self.gif.loop_count if self.gif.loop_count != 0
                else 'infinite'
            ),
            'file: {}'.format(self.gif.filename),
        ]

    def draw(self):
        """Draw the current animation state."""
        if self.is_scaled:
            # scale the gif to fill the window
            scale_factor = min(
                float(self.size[0]) / self.gif.size[0],
                float(self.size[1]) / self.gif.size[1]
            )
            scaled_size = (
                int(self.gif.size[0] * scale_factor),
                int(self.gif.size[1] * scale_factor)
            )
            scaled_frame = pygame.transform.scale(self.current_frame,
                                                  scaled_size)
        else:
            # no scaling
            scaled_size = self.gif.size
            scaled_frame = self.current_frame

        # position to draw frame so it is centered
        frame_pos = (self.size[0] / 2 - scaled_size[0] / 2,
                     self.size[1] / 2 - scaled_size[1] / 2)
        # draw the background over the entire window
        # this also clears the previous frame, so transparency works correctly
        for x in range(0, self.size[0], self.bg_surface.get_width()):
            for y in range(0, self.size[1], self.bg_surface.get_height()):
                self.screen.blit(self.bg_surface, (x, y))
        # draw border around the frame
        pygame.draw.rect(self.screen, (255, 0, 0), (
            frame_pos[0] - 1, frame_pos[1] - 1,
            scaled_size[0] + 2, scaled_size[1] + 2
        ), 1)
        # draw the frame
        self.screen.blit(scaled_frame, frame_pos)
        # draw info
        if self.is_showing_info:
            left = 5
            current_y = 5
            for line in self.info_lines:
                font_surface = self.font.render(line, True, (0, 0, 0),
                                                (255, 255, 255))
                font_surface.set_alpha(200)
                self.screen.blit(font_surface, (left, current_y))
                current_y += font_surface.get_height() + 2

        pygame.display.flip()

    def show(self):
        """Show the GUI and enter the main event loop."""
        now = 0
        while not self.is_exiting:
            elapsed = pygame.time.get_ticks() - now
            now = pygame.time.get_ticks()
            self.update(elapsed)
            self.draw()
            self.handle_events()
            self.clock.tick(self.fps)
