#!/usr/bin/env python3

import sys
import gi
import logging

gi.require_version('Gst', '1.0')

from gi.repository import Gst

logging.basicConfig(level=logging.DEBUG, format="[%(name)s] [%(levelname)8s - %(message)s]")
logger = logging.getLogger(__name__)


class Player(object):
    '''A pipeline manually for a player by instantiating each element and linking them all together'''
    def __init__(self, pattern=1) -> None:
        Gst.init(sys.argv[1:])

        # Create the elements
        source = Gst.ElementFactory.make("videotestsrc", "source")
        filter0 = Gst.ElementFactory.make("vertigotv", "filter")
        convert = Gst.ElementFactory.make("videoconvert", "convert")
        sink = Gst.ElementFactory.make("autovideosink", "sink")

        pipeline = Gst.Pipeline.new("test-pipeline")

        if not pipeline or not source or not filter0 or not convert or not sink:
            logger.error("Not all elements could be created.")
            sys.exit(1)

        pipeline.add(source, filter0, convert, sink)
        if not source.link(filter0) or not filter0.link(convert) or not convert.link(sink):
            logger.error("Element could not be linked.")
            sys.exit(1)

        source.props.pattern = pattern

        ret = pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            logger.error("Unable to set the pipeline to the playing state.")
            sys.exit(1)

        bus = pipeline.get_bus()
        msg = bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.ERROR | Gst.MessageType.EOS)

        if msg:
            if msg.type == Gst.MessageType.ERROR:
                err, debug_info = msg.parse_error()
                logger.error(f"Error received from element {msg.src.get_name()}: {err.message}")
                logger.error(f"Debugging information: {debug_info if debug_info else 'none'}")
            elif msg.type == Gst.MessageType.EOS:
                logger.info("End-Of-Stream reached.")
            else:
                logger.error("Unexpected message received.")

        pipeline.set_state(Gst.State.NULL)


if __name__ == "__main__":
    if len(sys.argv) < 2:
         pattern = 1
    pattern = int(sys.argv[1])
    p = Player(pattern)