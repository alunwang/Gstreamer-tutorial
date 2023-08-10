#!/usr/bin/env python3

import sys
import gi

gi.require_version('Gst', '1.0')

from gi.repository import Gst


class Player(object):
    '''Simple pipeline for a player'''
    def __init__(self, uri="https://gstreamer.freedesktop.org/data/media/sintel_trailer-480p.webm") -> None:
        # Init Gstreamer framework
        Gst.init(sys.argv[1:])

        pipeline_description="playbin uri=" + uri
        pipeline = Gst.parse_launch(pipeline_description)

        pipeline.set_state(Gst.State.PLAYING)

        bus = pipeline.get_bus()
        message = bus.timed_pop_filtered(
            Gst.CLOCK_TIME_NONE,
            Gst.MessageType.ERROR | Gst.MessageType.EOS
        )

        pipeline.set_state(Gst.State.NULL)


if __name__ == "__main__":
    uri = sys.argv[1]
    p = Player(uri)