"""Graphical user interface for viewing GIF animations."""

import pygame
import multiprocessing
import multiprocessing.pool

from gifprime.util import readable_size, static_path


pygame.init()
pygame.font.init()
POOL = multiprocessing.pool.ThreadPool(processes=1)


class LazyFrames(object):
    """Lazy GIF image 'generator'."""

    def __init__(self, gif):
        self.gif = gif
        self.surfaces = {}
        self.current = 0
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
        if self.gif.loop_count == 0:
            return True
        else:
            is_last_loop = self.loop_count == self.gif.loop_count - 1
            is_last_frame = self.current == len(self.gif.images) - 1
            return not (is_last_loop and is_last_frame)

    def next(self):
        """Advance to the next frame."""
        self.shown_count += 1
        self.current = (self.current + 1) % len(self.gif.images)

    def has_prev(self):
        """Returns True iff. there is a previous frame."""
        return self.shown_count > 0

    def prev(self):
        """Move to the previous frame."""
        self.shown_count -= 1
        self.current = (self.current - 1) % len(self.gif.images)

    @property
    def current_frame(self):
        return self.get_surface(self.current)

    @property
    def loop_count(self):
        return self.shown_count / len(self.gif.images)


class GIFViewer(object):
    """Graphical GIF animation viewer."""

    # minimum size that the window will open at
    MIN_SIZE = (400, 250)

    def __init__(self, load_gif_f, fps=60):
        self.gif = None
        self.fps = fps

        self.is_loading = True
        self.is_playing = True
        self.is_reversed = False
        self.is_scaled = False
        self.is_exiting = False
        self.is_showing_info = False

        self.bg_surface = pygame.image.load(static_path('background.png'))
        self.font = pygame.font.Font(static_path('DroidSansMono.ttf'), 14)
        self.frames = None
        self.current_frame = None
        self.frame_delay = 0
        self.ms_since_last_frame = 0
        self.info_lines = None

        # Setup pygame stuff
        self.size = self.MIN_SIZE
        self.set_title()
        self.screen = None
        self.set_screen()
        self.clock = pygame.time.Clock()

        self.async_result = POOL.apply_async(load_gif_f)

    def check_loading(self):
        """Check if the gif has finished loading."""
        try:
            # TODO: error handling
            gif = self.async_result.get(False)
        except multiprocessing.TimeoutError:
            return
        self.is_loading = False
        self.gif = gif
        self.frames = LazyFrames(gif)
        self.set_title()
        self.size = (max(self.MIN_SIZE[0], self.gif.size[0]),
                     max(self.MIN_SIZE[1], self.gif.size[1]))
        self.set_screen()

    def set_title(self):
        """Set the window title."""
        if self.is_loading:
            name = "Loading..."
        else:
            name = self.gif.filename.split('/')[-1]
        pygame.display.set_caption('{} - gifprime'.format(name))


    def set_screen(self):
        """Set the video mode and self.screen.

        Called on init or when the window is resized.
        """
        self.screen = pygame.display.set_mode(self.size, pygame.RESIZABLE)

    def show_next_frame(self, backwards=False):
        """Switch to the next frame, or do nothing if there isn't one."""
        if self.is_loading:
            return
        if self.current_frame is None:
            self.current_frame, self.frame_delay = self.frames.current_frame
        elif not backwards and self.frames.has_next():
            self.frames.next()
            self.current_frame, self.frame_delay = self.frames.current_frame
            self.ms_since_last_frame = 0
        elif backwards and self.frames.has_prev():
            self.frames.prev()
            self.current_frame, self.frame_delay = self.frames.current_frame
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
                if event.key in [pygame.K_ESCAPE, pygame.K_q]:
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

    def update_loading(self, elapsed):
        pass

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
            'size: {}x{}'.format(self.gif.size[0], self.gif.size[1]),
            'loop: {} / {}'.format(self.frames.loop_count + 1,
                                   self.gif.loop_count or 'infinite'),
            'frame: {} / {} ({} ms delay)'.format(self.frames.current + 1,
                                                  len(self.gif.images),
                                                  self.frame_delay),
            'compression ratio: {:.2%} ({} / {})'.format(
                float(self.gif.compressed_size) / self.gif.uncompressed_size,
                readable_size(self.gif.compressed_size),
                readable_size(self.gif.uncompressed_size),
            ),
        ]

    def draw_loading(self):
        self.screen.fill((220, 220, 220))
        pygame.display.flip()

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
        self.screen.fill((220, 220, 220))
        frame_right = frame_pos[0] + scaled_size[0]
        frame_bottom = frame_pos[1] + scaled_size[1]
        for x in range(frame_pos[0], frame_right, self.bg_surface.get_width()):
            for y in range(frame_pos[1], frame_bottom,
                           self.bg_surface.get_height()):
                self.screen.blit(self.bg_surface, (x, y),
                                 (0, 0, frame_right - x, frame_bottom - y))
        # draw border around the frame
        pygame.draw.rect(self.screen, (255, 255, 255), (
            frame_pos[0] - 1, frame_pos[1] - 1,
            scaled_size[0] + 2, scaled_size[1] + 2
        ), 1)
        pygame.draw.rect(self.screen, (150, 150, 150), (
            frame_pos[0] - 2, frame_pos[1] - 2,
            scaled_size[0] + 4, scaled_size[1] + 4
        ), 1)
        # draw the frame
        self.screen.blit(scaled_frame, frame_pos)
        # draw info
        if self.is_showing_info:
            left = 5
            current_y = 5
            for line in self.info_lines:
                font_surface = self.font.render(line.strip(), True, (0, 0, 0),
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
            if not self.is_loading:
                self.update(elapsed)
                self.draw()
            else:
                self.update_loading(elapsed)
                self.draw_loading()
                self.check_loading()
            self.handle_events()
            self.clock.tick(self.fps)
