"""Offline MP4 validation only. No rendering, TTS, network, autoplay or case writes."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import unquote, urlsplit
from PIL import Image

ORIGIN = 'authored_local_media_derivative'
MAX_BYTES = 30_000_000
VOICE = {'engine':'macos_say','voice':'Samantha','ordinary_stock':True,'voice_clone':False}

def require(ok, message):
    if not ok: raise ValueError(message)

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def text_sha(text): return hashlib.sha256(text.encode()).hexdigest()
def digest(value, name):
    require(isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value), name+' must be SHA256')

def public_file(public, src, suffix=None):
    require(isinstance(src,str) and src, 'nonempty local media path required')
    u=urlsplit(src);require(not u.scheme and not u.netloc and not u.query and not u.fragment,'external/query/fragment media URL forbidden')
    decoded=unquote(u.path);require(not any(x in decoded for x in ['\x00','\\','?','#']), 'invalid local media path')
    require('..' not in Path(decoded).parts, 'path traversal forbidden')
    path=public/decoded.lstrip('/')
    if not path.exists():
        from scamworld.corpus.neutral_names import served_file   # construction assets are served under neutral names
        path=served_file(public,decoded) or path
    require(not path.is_symlink(),'symlink media forbidden');path=path.resolve()
    require(path.is_relative_to(public.resolve()) and path.is_file(),'media missing or outside public root')
    if suffix:require(path.suffix.lower()==suffix, 'MP4 extension required')
    return path

def case_file(case, value, build_only=False):
    require(isinstance(value,str) and value, 'local provenance path required')
    require(not urlsplit(value).scheme and not urlsplit(value).query and not urlsplit(value).fragment,'nonlocal provenance path')
    p=Path(value);require(p.is_absolute() and not p.is_symlink() and p.is_file(),'absolute local provenance file required')
    p=p.resolve();root=case/'records/build' if build_only else case
    require(p.is_relative_to(root.resolve()),'provenance path escaped this case')
    return p

def arg_value(argv, flag):
    require(argv.count(flag)==1 and argv.index(flag)+1<len(argv),'unique command argument required: '+flag)
    return argv[argv.index(flag)+1]

def check_media(public, media, *, allow_engineering_fixture=False, probe_runner=subprocess.run):
    public=Path(public).resolve();case=public.parent
    require(isinstance(media,dict) and media.get('kind')=='video','real video media object required')
    require(media.get('origin')==ORIGIN,'local derivative origin required, never Grok video')
    require(media.get('autoplay') is False and media.get('loop') is False and media.get('controls') is True,
            'explicit controls/no-autoplay/no-loop policy required')
    require(media.get('preload')=='metadata','metadata preload required')
    video=public_file(public,media.get('src'),'.mp4');require(0<video.stat().st_size<=MAX_BYTES,'MP4 exceeds30MB or empty')
    digest(media.get('sha256'),'video sha');require(sha(video)==media['sha256'],'video hash mismatch')
    with video.open('rb') as stream:header=stream.read(12)
    require(len(header)==12 and header[4:8]==b'ftyp','not an MP4 container')
    poster=public_file(public,media.get('poster_src'));digest(media.get('poster_sha256'),'poster sha')
    require(sha(poster)==media['poster_sha256'],'poster hash mismatch')
    with Image.open(poster) as image:
        require(image.width>0 and image.height>0 and image.width*image.height<=40_000_000,'invalid poster dimensions');image.verify()
    transcript=media.get('transcript');require(isinstance(transcript,str) and transcript.strip() and len(transcript)<=4000,'plain bounded transcript required')
    require('[[' not in transcript and ']]' not in transcript and not any(ord(c)<32 and c not in '\n\t\r' for c in transcript),'TTS directives/control text forbidden')
    digest(media.get('transcript_sha256'),'transcript sha');require(text_sha(transcript)==media['transcript_sha256'],'transcript hash mismatch')
    provenance=media.get('provenance');require(isinstance(provenance,dict) and provenance.get('method')=='macos_say_ffmpeg','explicit local TTS/ffmpeg provenance required')
    require(provenance.get('stock_voice')==VOICE,'ordinary Samantha stock voice required; no voice cloning')
    require(provenance.get('claimed_grok_video',False) is False,'local derivative cannot be claimed as Grok video')
    for field in ['external_calls','paid_calls']:
        require(provenance.get(field,0)==0,'local media cannot record external/paid calls')
    receipt_path=case_file(case,provenance.get('receipt_path'),True);digest(provenance.get('receipt_sha256'),'receipt sha')
    require(sha(receipt_path)==provenance['receipt_sha256'],'receipt hash mismatch');receipt=json.loads(receipt_path.read_text())
    require(isinstance(receipt,dict) and type(receipt.get('schema_version')) is int and receipt['schema_version']==1,'receipt schema1 required')
    fixture=receipt.get('engineering_fixture') is True;require(not fixture or allow_engineering_fixture,'engineering fixture cannot certify production media')
    require(receipt.get('case_id',case.name)==case.name,'receipt belongs to another case')
    require(receipt.get('origin')==ORIGIN and receipt.get('stock_voice')==VOICE,'receipt derivative/stock voice mismatch')
    for key,expected in [('poster_sha256',media['poster_sha256']),('transcript_sha256',media['transcript_sha256']),('output_sha256',media['sha256'])]:require(receipt.get(key)==expected,'receipt source/output hash mismatch: '+key)
    tpath=case_file(case,receipt.get('transcript_path'),True);require(tpath.read_bytes()==transcript.encode(),'TTS transcript file differs')
    commands=receipt.get('commands');require(isinstance(commands,dict),'command receipts required')
    for stage in ['say','ffmpeg']:
        record=commands.get(stage);require(isinstance(record,dict) and type(record.get('exit_code')) is int and record['exit_code']==0,'successful '+stage+' command receipt required')
        argv=record.get('argv');require(isinstance(argv,list) and argv and all(isinstance(a,str) and a for a in argv),'argv list required')
        require(Path(argv[0]).name==stage,'wrong command executable')
        require(not any(re.search(r'(?:https?|ftp|rtmp|rtsp|tcp|udp)://',a,re.I)for a in argv),'network command URL forbidden')
        for field in ['stdout_sha256','stderr_sha256']:digest(record.get(field),stage+' '+field)
    say=commands['say']['argv'];require(say[0]=='/usr/bin/say' and arg_value(say,'-v')=='Samantha','stock macOS say Samantha command required')
    require(case_file(case,arg_value(say,'-f'),True)==tpath,'say command transcript mismatch')
    audio=case_file(case,arg_value(say,'-o'),True)
    enc=commands['ffmpeg']['argv'];inputs=[enc[i+1]for i,v in enumerate(enc[:-1])if v=='-i'];require(len(inputs)==2,'poster and stock-narration inputs required')
    require(case_file(case,inputs[0])==poster and case_file(case,inputs[1],True)==audio,'ffmpeg source inputs differ')
    require(Path(enc[-1]).resolve()==video,'ffmpeg output path differs')
    for i,value in enumerate(enc[:-1]):
        if value=='-protocol_whitelist':require(set(enc[i+1].split(','))<={'file','pipe'},'ffmpeg network protocols forbidden')
    probe=shutil.which('ffprobe');require(probe is not None,'local ffprobe unavailable')
    argv=[probe,'-v','error','-protocol_whitelist','file','-f','mov','-use_absolute_path','0','-enable_drefs','0','-threads','1','-count_frames','-show_streams','-show_format','-of','json',str(video)]
    try:response=probe_runner(argv,capture_output=True,text=True,timeout=20,stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired as error:raise ValueError('local ffprobe timed out') from error
    require(response.returncode==0,'local ffprobe failed');info=json.loads(response.stdout);streams=info.get('streams',[])
    vs=[x for x in streams if x.get('codec_type')=='video'];aus=[x for x in streams if x.get('codec_type')=='audio']
    require(len(vs)==1 and len(aus)==1 and len(streams)==2,'exactly one video and one audio stream required')
    require(vs[0].get('codec_name')=='h264' and aus[0].get('codec_name')=='aac','H264 video + AAC audio required')
    try:duration=float(info['format']['duration']);frames=int(vs[0]['nb_read_frames'])
    except (KeyError,TypeError,ValueError)as error:raise ValueError('actual duration/frame count unavailable')from error
    require(math.isfinite(duration) and 2<=duration<=30,'video duration must be2–30seconds');require(frames>=2,'at least2decoded video frames required')
    require(sha(video)==media['sha256'] and sha(poster)==media['poster_sha256'] and sha(receipt_path)==provenance['receipt_sha256'] and tpath.read_bytes()==transcript.encode(),'media/provenance changed during probe')
    return {**media,'inspection':{'video_bytes':video.stat().st_size,'duration_seconds':duration,'decoded_video_frames':frames,'video_codec':'h264','audio_codec':'aac','ffprobe_argv':argv,'ffprobe_stdout_sha256':text_sha(response.stdout),'receipt_mode':'engineering_fixture_only'if fixture else'local_command_receipts_and_real_file_probe','browser_verification':'still required: initial paused/no-autoplay, native controls, local playback advances with user action','source_identity_scope':'Fictional Grok portrait and ordinary stock narration; no actual person voice/endorsement attested.'}}

def main():
    p=argparse.ArgumentParser();p.add_argument('--public',type=Path,required=True);p.add_argument('--media',type=Path,required=True);a=p.parse_args();obj=json.loads(a.media.read_text());obj=obj['items'][0]['media']if 'items'in obj else obj;print(json.dumps(check_media(a.public,obj),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
