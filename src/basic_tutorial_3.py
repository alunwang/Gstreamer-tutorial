#!/usr/bin/env python3

import sys
import gi
import logging

gi.require_version('Gst', '1.0')

from gi.repository import Gst

logging.basicConfig(level=logging.DEBUG, format="[%(name)s] [%(levelname)8s - %(message)s]")
logger = logging.getLogger(__name__)


class Player(object):
    '''Dynamically build a pipeline for a player'''
    def __init__(self, uri="https://gstreamer.freedesktop.org/data/media/sintel_trailer-480p.webm"):
        Gst.init(sys.argv[1:])

        self.source = Gst.ElementFactory.make("uridecodebin", "source")
        self.convert = Gst.ElementFactory.make("audioconvert", "convert")
        self.resample = Gst.ElementFactory.make("audioresample", "resample")
        self.sink = Gst.ElementFactory.make("autoaudiosink", "sink")

        self.pipeline = Gst.Pipeline.new("test-pipeline")
        if not self.source or not self.convert or not self.resample or not self.sink or not self.pipeline:
            logger.error("Not all elements could be created.")
            sys.exit(1)

        self.pipeline.add(self.source, self.convert, self.resample, self.sink)
        if not self.convert.link(self.resample) or not self.resample.link(self.sink):
            logger.error("Elements could not be linked.")
            sys.exit(1)

        self.source.set_property("uri", uri)
        self.source.connect("pad-added", self.on_pad_added)

        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            logger.error("Unable to set the pipeline to the playing state.")
            sys.exit(1)

        bus = self.pipeline.get_bus()
        terminate = False
        while True:
            msg = bus.timed_pop_filtered(
                Gst.CLOCK_TIME_NONE,
                Gst.MessageType.STATE_CHANGED | Gst.MessageType.EOS | Gst.MessageType.ERROR
            )
            if not msg:
                continue
            t = msg.type
            if t == Gst.MessageType.ERROR:
                err, debug_info = msg.parse_error()
                logger.error(f"Error received from element {msg.src.get_name()}: {err.message}")
                logger.error(f"Debugging information: {debug_info if debug_info else 'none'}")
                terminate = True
            elif t == Gst.MessageType.EOS:
                logger.info("End-Of-Stream reached.")
                terminate = True
            elif t == Gst.MessageType.STATE_CHANGED:
                if msg.src == self.pipeline:
                    old_state, new_state, pending_state = msg.parse_state_changed()
                    logger.info(f"Pipeline state changed from {Gst.Element.state_get_name(old_state)} \
                                to {Gst.Element.state_get_name(new_state)}")

            else:
                logger.error("Unexpected message received.")
                terminate = True
            
            if terminate:
                break
        
        self.pipeline.set_state(Gst.State.NULL)

    def on_pad_added(self, src, new_pad):
        sink_pad = self.convert.get_static_pad("sink")
        logger.info(f"Received new pad {new_pad.get_name()} \
                    from {src.get_name()}")
        
        if (sink_pad.is_linked()):
            logger.info("We are already linked. Ignoring.")
            return
        
        new_pad_caps = new_pad.get_current_caps()
        new_pad_struct = new_pad_caps.get_structure(0)
        new_pad_type = new_pad_struct.get_name()

        if not new_pad_type.startswith("audio/x-raw"):
            logger.info(f"It has type {new_pad_type} which is not raw audio. Ignoring.")
            return
        
        ret = new_pad.link(sink_pad)
        if not ret == Gst.PadLinkReturn.OK:
            logger.info(f"Type is {new_pad_type} but link failed.")
        else:
            logger.info(f"Link succeeded (type {new_pad_type})")

        return


if __name__ == '__main__':
    if len(sys.argv) < 2:
        logger.error("You missed the required argument.")
        logger.info(f"Usage: {__file__} uri")
        sys.exit(1)
    
    uri = sys.argv[1]
    logger.info(f"You are playing: {uri}")
    player = Player(uri)