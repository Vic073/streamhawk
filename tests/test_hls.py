"""
Tests for M3U8 parser.
"""
import unittest

from streamhawk.hls import M3U8Parser, M3U8Stream


class TestM3U8Parser(unittest.TestCase):
    """Test cases for M3U8 parser."""
    
    def test_parse_master_playlist(self):
        """Test parsing master playlist."""
        content = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-STREAM-INF:BANDWIDTH=800000,RESOLUTION=640x360
360p.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=2800000,RESOLUTION=1280x720
720p.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=5000000,RESOLUTION=1920x1080
1080p.m3u8
"""
        
        parser = M3U8Parser()
        parser.parse(content, base_url="https://example.com/")
        
        self.assertTrue(parser.is_master)
        self.assertEqual(len(parser.streams), 3)
        
        # Check stream resolutions
        resolutions = [s.resolution for s in parser.streams]
        self.assertIn("640x360", resolutions)
        self.assertIn("1280x720", resolutions)
        self.assertIn("1920x1080", resolutions)
    
    def test_parse_media_playlist(self):
        """Test parsing media playlist."""
        content = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:10
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:10.000,
segment0.ts
#EXTINF:10.000,
segment1.ts
#EXT-X-ENDLIST
"""
        
        parser = M3U8Parser()
        parser.parse(content)
        
        self.assertFalse(parser.is_master)
        self.assertEqual(parser.target_duration, 10)
        self.assertEqual(parser.media_sequence, 0)
    
    def test_get_best_stream(self):
        """Test getting best quality stream."""
        parser = M3U8Parser()
        parser.streams = [
            M3U8Stream(bandwidth=800000, resolution="640x360", url="360p.m3u8"),
            M3U8Stream(bandwidth=2800000, resolution="1280x720", url="720p.m3u8"),
            M3U8Stream(bandwidth=5000000, resolution="1920x1080", url="1080p.m3u8"),
        ]
        
        best = parser.get_best_stream()
        self.assertEqual(best.resolution, "1920x1080")
        self.assertEqual(best.bandwidth, 5000000)
    
    def test_get_best_stream_with_limit(self):
        """Test getting best stream with resolution limit."""
        parser = M3U8Parser()
        parser.streams = [
            M3U8Stream(bandwidth=800000, resolution="640x360", url="360p.m3u8"),
            M3U8Stream(bandwidth=2800000, resolution="1280x720", url="720p.m3u8"),
            M3U8Stream(bandwidth=5000000, resolution="1920x1080", url="1080p.m3u8"),
        ]
        
        best_720p = parser.get_best_stream(max_resolution="720p")
        self.assertEqual(best_720p.resolution, "1280x720")
    
    def test_stream_height_property(self):
        """Test stream height extraction."""
        stream = M3U8Stream(bandwidth=1000000, resolution="1920x1080")
        self.assertEqual(stream.height, 1080)
        self.assertEqual(stream.width, 1920)


if __name__ == "__main__":
    unittest.main()
