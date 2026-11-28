import io,zipfile,hashlib
import numpy as np
import soundfile as sf
import pytest
from skell_sound_match.wav_only.corpus_index import index_archives

def test_inventory(tmp_path):
    p=tmp_path/'source.zip';buf=io.BytesIO();sf.write(buf,np.zeros((100,2)),44100,format='WAV',subtype='PCM_24');data=buf.getvalue()
    with zipfile.ZipFile(p,'w') as z:
        z.writestr('dry.wav',data);z.writestr('duplicate.wav',data);z.writestr('preset.fst',b'private');z.writestr('note.txt','ignore')
    rows=index_archives([p]);assert len(rows)==3 and rows[0]['sha256']==rows[1]['sha256']==hashlib.sha256(data).hexdigest();assert rows[0]['frames']==100 and rows[0]['rate']==44100 and rows[0]['channels']==2;assert 'frames' not in rows[2];assert len(list(tmp_path.iterdir()))==1

def test_duplicate_name(tmp_path):
    p=tmp_path/'duplicate.zip'
    with zipfile.ZipFile(p,'w') as z:
        z.writestr('preset.fst',b'a')
        with pytest.warns(UserWarning):z.writestr('preset.fst',b'b')
    with pytest.raises(ValueError):index_archives([p])
