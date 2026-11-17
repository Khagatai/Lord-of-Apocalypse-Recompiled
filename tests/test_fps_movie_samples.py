import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('fps_check',Path(__file__).resolve().parents[1]/'tools/check-gameplay-fps.py')
fps=importlib.util.module_from_spec(spec);spec.loader.exec_module(fps)

class MovieSamples(unittest.TestCase):
    def test_global_counters_do_not_misalign_a_restarted_movie(self):
        lines=[]
        for run,length in ((0,2),(1,20)):
            lines.append('LOA_FPS: media event=0 key=1234')
            for n in range(1,length+1):
                lines.append(f'MpegAvcDecode #{n+run*50} buf=x pts={n*3003} dec=1 frames={n}')
                lines.append(f'MpegGetAtracAu #{n+run*50} pts={351+(n-1)*4180}')
            lines.append('LOA_FPS: media event=1 key=1234')
        pts=fps.movie_pts('\n'.join(lines))
        self.assertEqual(len(pts['video']),20)
        self.assertEqual(pts['video'][1],3003)
        self.assertEqual(pts['audio'][1],351)

    def test_retimestamps_and_missing_samples_cannot_pass(self):
        base={i:i*3003 for i in range(1,21)}
        a=dict(movie_video_pts=base,movie_audio_pts=base)
        b=dict(movie_video_pts=dict(base),movie_audio_pts=dict(base))
        self.assertTrue(all(v['identical'] for v in fps.compare_movie_pts({'30':a,'60':b}).values()))
        b['movie_video_pts'][10]+=1
        self.assertFalse(fps.compare_movie_pts({'30':a,'60':b})['video']['identical'])
        b['movie_audio_pts']={1:3003}
        self.assertFalse(fps.compare_movie_pts({'30':a,'60':b})['audio']['identical'])

    def test_sparse_audio_counters_align_by_au_interval_after_restart(self):
        video={i:i*3003 for i in range(1,21)}
        a={i:351+(i-1)*4180 for i in (1,2,3,4,256,512)}
        b={i:351+(i-1)*4180 for i in (1,2,3,243,499,755)}
        runs={'30':dict(movie_video_pts=video,movie_audio_pts=a),'60':dict(movie_video_pts=video,movie_audio_pts=b)}
        self.assertTrue(fps.compare_movie_pts(runs)['audio']['identical'])
        b[755]+=1
        self.assertFalse(fps.compare_movie_pts(runs)['audio']['identical'])
