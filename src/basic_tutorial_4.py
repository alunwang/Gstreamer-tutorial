#!/usr/bin/env python3

import gi
import sys
import logging

gi.require_version('Gst', '1.0')

from gi.repository import Gst
from helper import format_ns

logging.basicConfig(level=logging.DEBUG, format="[%(name)s] [%(levelname)8s - %(message)s]")
logger = logging.getLogger(__name__)


class Player(object):
    '''
    Ask the pipeline if seeking is allowed, if allowed, seek to a location
    '''
    def __init__(self, uri="https://gstreamer.freedesktop.org/data/media/sintel_trailer-480p.webm") -> None:
        Gst.init(sys.argv[1:])

        self.playing = False
        self.terminate = False
        self.seek_enable = False
        self.seek_done = False
        self.duration = Gst.CLOCK_TIME_NONE

        # Create the elements
        self.playbin = Gst.ElementFactory.make("playbin", "playbin")

        if not self.playbin:
            logger.error("Not all elements could be created.")
            sys.exit(1)
        
        self.playbin.set_property("uri", uri)

    def play(self):
        if self.playing:
            return

        # Start playing
        ret = self.playbin.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            logger.error("Unable to set the pipeline to the playing state.")
            sys.exit(1)

        try:
            # Listen to the bus
            bus = self.playbin.get_bus()
            while True:
                msg = bus.timed_pop_filtered(
                100 * Gst.MSECOND, # Timeout=100ms: it returns NULL (wake up) every 100ms even without message so that "UI" can be updated.
                Gst.MessageType.STATE_CHANGED | Gst.MessageType.EOS | Gst.MessageType.ERROR | Gst.MessageType.DURATION_CHANGED
                )
                if msg:
                    self.handle_message(msg)
                else:
                    # We got no message, this means the timeout expired
                    if self.playing:
                        current = -1

                        # Query the current position of the stream
                        ret, current = self.playbin.query_position(Gst.Format.TIME)
                        if not ret:
                            logger.error("Could not query current position.")
                        # If we don't know it yet, query the stream duration
                        if self.duration == Gst.CLOCK_TIME_NONE:
                            (ret, self.duration) = self.playbin.query_duration(Gst.Format.TIME)
                            if not ret:
                                logger.error("Could not query stream duration")
                        
                        # Print current position and total duration
                        logger.info(f"Position {format_ns(current)} / {format_ns(self.duration)}")

                        # If seeking is enabled, we have not done it yet and the time is right, seek
                        if self.seek_enable and not self.seek_done and current > 10 * Gst.SECOND:
                            logger.info("Reach 10s, performing seek ...")
                            self.playbin.seek_simple(
                                Gst.Format.TIME,
                                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                                30 * Gst.SECOND
                            )

                            self.seek_done = True
                if self.terminate:
                    break
        finally:
            self.playbin.set_state(Gst.State.NULL)

    def handle_message(self, msg):
        '''
        Process all kinds of messages.
        '''
        t = msg.type
        if t == Gst.MessageType.ERROR:
            err, debug_info = msg.parse_error()
            logger.error(f"{msg.src.get_name()}: {err}")
            if debug_info:
                logger.debug(f"{debug_info}")
            self.terminate = True
        elif t == Gst.MessageType.EOS:
            logger.info("End-Of-Stream reached")
            self.terminate = True
        elif t == Gst.MessageType.DURATION_CHANGED:
            # The duration has changed, invalidate the current one
            self.duration = Gst.CLOCK_TIME_NONE
        elif t == Gst.MessageType.STATE_CHANGED:
            old, new, pending = msg.parse_state_changed()
            if msg.src == self.playbin:
                logger.info(f"Pipeline state changed from {Gst.Element.state_get_name(old)} to {Gst.Element.state_get_name(new)}")
                # Remember whether we are in the playing state or not
                self.playing = (new == Gst.State.PLAYING)

                if self.playing:
                    # We just move to PLAYING. Check if seeking is possible
                    query = Gst.Query.new_seeking(Gst.Format.TIME)
                    if self.playbin.query(query):
                        fmt, self.seek_enable, start, end = query.parse_seeking()
                        if self.seek_enable:
                            logger.info(f"Seeking is ENABLED (from {format_ns(start)} to {format_ns(end)})")
                        else:
                            logger.info("Seeking is DISABLED for this stream.")
                    else:
                        logger.error("Seeking query failed.")
        
        else:
            logger.error("Unexpected message arrive.")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        logger.error("You missed the required argument.")
        logger.info(f"Usage: {__file__} uri")
        sys.exit(1)
    
    uri = sys.argv[1]
    logger.info(f"You are playing: {uri}")
    p = Player(uri)
    p.play()