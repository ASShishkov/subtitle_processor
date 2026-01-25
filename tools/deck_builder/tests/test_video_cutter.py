import pytest
from video_cutter import parse_srt

def test_parse_srt():
    srt_content = "1\n00:00:01,000 --> 00:00:02,000\nHello world\n"
    with open("test.srt", "w", encoding="utf-8") as f:
        f.write(srt_content)
    result = parse_srt("test.srt", ["Hello world"])
    assert result == [("Hello world", 1.0, 2.0)]