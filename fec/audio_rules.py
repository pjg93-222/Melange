# -*- coding: utf-8 -*-
"""Shared duration, speech-unit, topic, and independence gates for every audio path.

The strict profile contract requires two independent programs and at least 30 seconds of
reviewer-confirmed target audio in every accepted clip.  The member floor therefore equals two
minimum clips (60 seconds); keeping a separate 180-second literal biased eligibility toward members
with unusually long clips and allowed the legacy and strict paths to drift apart.

Pitch-deviation profiles need repeated speech-level observations.  Five speech units is the hard
minimum at which a sample standard deviation is even minimally stable; at least two transcript-
identified topics prevent a one-topic sample from being mislabeled as the speaker's baseline.
"""

MIN_SEGMENT_SEC = 5.0
MIN_CLIP_TARGET_SEC = 30.0
MIN_CLIP_TARGET_WORDS = 50
MIN_INDEPENDENT_SOURCES = 2
MIN_INDEPENDENT_PROGRAMS = 2
MIN_MEMBER_TARGET_SEC = MIN_CLIP_TARGET_SEC * MIN_INDEPENDENT_PROGRAMS
MIN_MEMBER_SPEECH_UNITS = 5
MIN_MEMBER_DISTINCT_TOPICS = 2
MIN_TOPIC_SPEECH_UNITS = 2

assert MIN_MEMBER_TARGET_SEC == 60.0
