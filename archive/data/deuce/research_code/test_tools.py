#!/usr/bin/env python3
import hashlib, json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from fst_inspector import inspect,read_events,FSTFormatError
from stage_audit import bands_diff
import numpy as np
class InspectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder=Path(__file__).parents[1]/'sources'
        cls.rec=cls.folder/'rec deuce.fst';cls.main=cls.folder/'main deuce.fst'
    def test_valid_mixer_chain(self):
        a=inspect(self.rec);b=inspect(self.main)
        self.assertEqual(a['track_name'],'REC');self.assertEqual(b['track_name'],'MAIN')
        self.assertEqual([x['slot_index'] for x in a['slots']],[0,1,2,3])
        self.assertEqual([x['slot_index'] for x in b['slots']],[0,1,2,3,4,6,7,8])
        self.assertEqual(b['empty_slots_before_last_plugin'],[5])
    def test_two_distinct_soundgoodizers(self):
        a=inspect(self.rec);b=inspect(self.main)
        ra=next(x for x in a['slots'] if x['slot_name']=='Soundgoodizer')
        rb=next(x for x in b['slots'] if x['slot_name']=='Soundgoodizer')
        self.assertEqual((ra['native_state']['mode_index'],ra['native_state']['amount_raw_integer']),(0,43))
        self.assertEqual((rb['native_state']['mode_index'],rb['native_state']['amount_raw_integer']),(2,503))
        self.assertIsNone(ra['native_state']['amount_percent'])
    def test_waves_active_xml(self):
        m=inspect(self.main);w=[x['waves'] for x in m['slots'] if x['waves']]
        self.assertEqual([x['plugin_name'] for x in w],['REQ','SSLChannel','DeEsser','C6','PuigTec EQP1A'])
        eq=w[0];self.assertTrue(eq['stereo_band_tokens_identical'])
        self.assertEqual([round(x['frequency_hz']) for x in eq['six_band_EQ_stored_values']],[92,206,414,3487,7828,11232])
        self.assertEqual(int(w[2]['deesser_candidate_frequency_hz']),5860)
    def test_reject_non_fst_and_truncated(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'broken.fst'
            f.write_bytes(b'foobar');self.assertRaises(FSTFormatError,read_events,f)
            f.write_bytes(self.rec.read_bytes()[:-9]);self.assertRaises(FSTFormatError,read_events,f)
    def test_nonfinite_state_not_executed(self):
        # No plugin loading, no evaluation of arbitrary input.
        src=Path(__file__).parent/'fst_inspector.py';txt=src.read_text()
        self.assertNotIn('eval(',txt)
        self.assertNotIn('subprocess',txt)
    def test_audio_analysis_identity(self):
        sr=44100;x=np.sin(np.arange(sr)*2*np.pi*1000/sr)*0.2
        d=bands_diff(x,x,sr)
        self.assertTrue(all(abs(y)<1e-8 for y in d.values()))
if __name__=='__main__':unittest.main(verbosity=2)
