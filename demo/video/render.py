#!/usr/bin/env python3
"""Render two captioned review edits from a verified capture. Requires Pillow + FFmpeg.
No synthetic app UI: the phone panel always comes from recorded simulator frames.
Answer panels show server history after reopening the app; holds are editorial.
"""
import argparse
import json
from pathlib import Path
import subprocess
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
W, H = 1920, 1080
BG, PANEL, INK, MUTED, BLUE, GREEN = '#10151c', '#19222d', '#f4f5f7', '#a5b4c5', '#6caeff', '#66d5b0'
FONT = '/System/Library/Fonts/Supplemental/Arial.ttf'
BOLD = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'


def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)


def wrap(draw, text, width, size=30, bold=False):
    lines = []
    for para in text.split('\n'):
        current = ''
        for word in para.split():
            attempt = f'{current} {word}'.strip()
            if draw.textlength(attempt, font=font(size, bold)) > width and current:
                lines.append(current)
                current = word
            else:
                current = attempt
        lines.append(current)
    return lines


def paragraph(draw, text, xy, width, size=30, fill=INK, bold=False, spacing=1.35):
    x, y = xy
    for line in wrap(draw, text, width, size, bold):
        draw.text((x, y), line, font=font(size, bold), fill=fill)
        y += int(size * spacing)
    return y


def background(scene, kind, index, total, out):
    im = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle((64, 52, 72, 86), fill=BLUE)
    d.text((92, 51), 'PATCHBAY VOICE', font=font(28, True), fill=INK)
    d.text((440, 55), 'PRODUCT DEMO' if kind == 'product' else 'ENGINEERING WALKTHROUGH', font=font(22), fill=MUTED)
    d.text((1725, 54), f'{index + 1:02d} / {total:02d}', font=font(22), fill=MUTED)
    phone_x = 1380 if kind == 'product' else 80
    phone_y, phone_w, phone_h = 124, 370, 804
    d.rounded_rectangle((phone_x - 10, phone_y - 10, phone_x + phone_w + 10, phone_y + phone_h + 10), radius=32, fill='#293443')
    d.text((phone_x, 948), 'ACTUAL iOS SIMULATOR', font=font(18), fill=MUTED)
    if kind == 'product':
        d.text((80, 157), scene['eyebrow'], font=font(24, True), fill=GREEN)
        y = paragraph(d, scene['title'], (80, 207), 1130, 66, bold=True, spacing=1.13)
        y = paragraph(d, scene['body'], (80, y + 40), 1080, 34, fill=MUTED)
        if scene.get('quote'):
            d.rounded_rectangle((80, y + 32, 1210, y + 195), radius=18, fill=PANEL)
            paragraph(d, scene['quote'], (108, y + 54), 1070, 29, fill=GREEN)
        d.text((80, 873), scene.get('foot', 'Typed input • app refreshed for answer views • edited pacing'), font=font(23), fill=MUTED)
    else:
        x = 520
        paragraph(d, scene['title'], (x, 135), 1290, 48, bold=True, spacing=1.1)
        paragraph(d, scene['body'], (x, 210), 1270, 27, fill=MUTED)
        d.rounded_rectangle((x, 330, 1830, 730), radius=16, fill=PANEL)
        d.text((x + 24, 348), scene.get('panel_label', 'OBSERVED PI / SERVER EVENTS'), font=font(20, True), fill=GREEN)
        if scene.get('panel'):
            paragraph(d, scene['panel'], (x + 24, 395), 1230, 28, spacing=1.43)
        labels = ['INPUT', 'ASR', 'PI / INFERENCE', 'REPO / NOTES', 'TTS']
        for i, label in enumerate(labels):
            bx = x + i * 262
            active = i in scene.get('active', [])
            d.rounded_rectangle((bx, 778, bx + 230, 837), radius=12, outline=BLUE if active else '#46515e', width=2, fill=PANEL)
            d.text((bx + 15, 796), label, font=font(19, True), fill=INK if active else MUTED)
            if i < 4:
                d.line((bx + 234, 807, bx + 257, 807), fill=MUTED, width=2)
                d.polygon([(bx+257,807),(bx+250,803),(bx+250,811)], fill=MUTED)
                if i == 2:
                    d.polygon([(bx+234,807),(bx+241,803),(bx+241,811)], fill=MUTED)
        paragraph(d, scene.get('foot', 'Typed input bypasses ASR. Answer views refresh the app. Review edit is muted.'), (x, 869), 1280, 22, fill=MUTED)
    d.rectangle((0, 992, W, H), fill='#080c11')
    paragraph(d, scene['caption'], (90, 1010), 1740, 28, spacing=1.15)
    im.save(out)
    return phone_x, phone_y, phone_w, phone_h


def timestamp(seconds, vtt=False):
    ms = round(seconds * 1000)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f'{h:02}:{m:02}:{s:02}{"." if vtt else ","}{ms:03}'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('run', type=Path)
    p.add_argument('--only', choices=['product', 'engineering'])
    p.add_argument('--edit-file', type=Path, help='Use a revised edit-manifest.json')
    p.add_argument('--output', type=Path, default=ROOT / 'demo/video/output')
    args = p.parse_args()
    run, out = args.run.resolve(), args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((run / 'manifest.json').read_text())
    if 'recording_startup_offset_seconds' not in manifest:
        raise SystemExit('Run align.py and inspect the screenshot anchors before rendering')
    if not manifest.get('verified'):
        raise SystemExit('Capture must be verified before rendering')
    events = [json.loads(line) for line in (run / 'events.jsonl').read_text().splitlines()]
    started = manifest['recording_started_at'] + manifest.get('recording_startup_offset_seconds', 0)
    heard = [e['time'] for e in events if e.get('stage') == 'heard']
    done = [e['time'] for e in events if e['kind'] == 'response']
    def anchor(name):
        return float((run / (name + '.png.timestamp')).read_text()) - started
    ready, answer0, answer1 = [anchor(n) for n in ['01-ready', 'turn-0-answer', 'turn-1-answer']]
    note = (run / 'projects/patchbay-go/docs/patchbay/raw-route.md').read_text()
    (out / 'actual-note.md').write_text(note)
    scenes = {
      'product': [
        dict(duration=8, source=ready, eyebrow='YOUR CODEBASE, WITH YOU', title='Ask about the code.\nKeep the useful part.', body='A phone interface to a coding agent running beside your repositories.', caption='Patchbay Voice helps you understand a repository and save useful notes.'),
        dict(duration=12, source=heard[0]-started-5, eyebrow='01 / ASK', title='A concrete question.\nA real repository.', body='What does the raw route refuse? How does a valid link open its app?', quote='Demo project: Patchbay Go\nInput: typed in the real iOS app', caption='This recording uses typed input. Hold-to-talk uses the same agent after transcription.'),
        dict(duration=13, source=answer0, eyebrow='02 / UNDERSTAND', title='An answer grounded\nin the implementation.', body='The agent read the worker source. Its reply explains the rejected schemes and the redirect fallback. The follow-up adds a note with the status code.', quote='The response is real. The footage is edited for pacing.', caption='A correct answer needs the repository’s behavior, including the details that matter.'),
        dict(duration=12, source=heard[1]-started-5, eyebrow='03 / KEEP', title='Say what should\nbe remembered.', body='A follow-up asks for a contributor note. The saved detail can outlive the conversation.', caption='The next request saves those rules as a contributor note.'),
        dict(duration=12, source=answer1, eyebrow='04 / RETURN TO IT', title='A note on disk.\nA dedicated branch.', body='The note was written, committed, and pushed to an isolated local Git remote. The working branch stayed on develop.', quote='docs/patchbay/raw-route.md\nVerified local and remote notes commit match', caption='Note persistence is real here; the demonstration remote is local, not GitHub.'),
        dict(duration=9, source=answer1, eyebrow='FOCUSED BY DESIGN', title='Understand code.\nLeave notes.', body='No shell tool. No arbitrary source edits. Continuous voice is being researched; this build uses push-to-talk or text.', caption='Review edition: subtitles, no narration. Continuous conversation is proposed future work.')
      ],
      'engineering': [
        dict(duration=10, source=ready, title='One system, several distinct stages', body='The phone is the interface. Your server coordinates transcription, a pi turn, repository tools, notes and speech.', panel='Actual iOS simulator at left\nObserved server and pi events at right\nLiteLLM small • isolated source copy • local Git remote', active=[0,2,3,4], caption='This is the current system. Audio stages are distinct from agent execution.'),
        dict(duration=10, source=heard[0]-started-5, title='Typed input joins after transcription', body='Voice uploads a completed clip to faster-whisper. This recorded request is typed, so it goes directly to the agent.', panel='POST /api/talk\nOne held request per turn\nSame-chat work waits on an in-memory lock\nNo durable submission inbox or token stream to the phone', active=[0,2], caption='Continuous listening and streaming inference are separate capabilities; neither is implied here.'),
        dict(duration=done[0]-heard[0]+3, source=heard[0]-started, title='Watch the agent inspect the repository', body='Actual events from this turn appear in order beside the recorded simulator footage. Tool timestamps are relative to submission.', live=0, active=[2,3], caption='These are observable tool calls, not hidden model reasoning. This processing segment plays at real speed.'),
        dict(duration=10, source=answer0, title='One reply, then an audio rendering', body='The reply is complete before the client receives audio URLs. The iOS client fetches the chunks before playback.', panel='First reply: redirect explained; HTTP status omitted\nValid URI: meta refresh + JavaScript fallback\nManual tap-through link remains available\nServer speech ran in the capture; this edit is muted', active=[4], caption='The spoken answer is a rendering of the reply. The current audio delivery is not live streaming.'),
        dict(duration=done[1]-heard[1]+3, source=heard[1]-started, title='A follow-up becomes a durable note', body='The existing pi session carries context. The write tool is fenced to the notes directory; server code handles optional Git persistence.', live=1, active=[2,3], caption='The second turn uses the earlier context and writes a real note. This processing segment plays at real speed.'),
        dict(duration=10, source=answer1, title='Verify the side effect independently', body='A spoken “saved” is not the check. Inspect the file, the notes branch and the destination ref.', panel='File exists: docs/patchbay/raw-route.md\nNotes branch: patchbay\nLocal ref equals disposable remote ref\nWorking branch: develop • no source edits', active=[3], caption='The remote is a local bare repository. No demo note was pushed to the real project’s GitHub repository.'),
        dict(duration=13, source=answer0, title='A real misunderstanding becomes an eval', body='A historical question about a repository’s raw route was answered as a question about the assistant’s own behavior.', panel_label='BEHAVIORAL EVALUATION • RECORDED BASELINE', panel='Preserve capture → label expected behavior → freeze corpus\nCandidate and grader: LiteLLM small\nStrict Pydantic validation of grading output\n3 / 4 development cases passed; missing HTTP 400 remains', active=[2], caption='This take also omits the status in its first reply. Four eval cases are a starting corpus, not a broad benchmark.'),
        dict(duration=11, source=answer1, title='Next: continuous conversation, measured', body='Research starts with foreground listening, local speech detection and the existing server. Pocket operation is desirable, not a release prerequisite.', panel='Compare: interrupt playback vs capture a follow-up\nMeasure: cutoffs, false turns, delay and device impact\nSeparate: stop audio, cancel inference, completed note effects\nNo hot-mic implementation is claimed in this demo', active=[0,1,4], caption='A physical-device experiment should decide the next architecture, rather than the diagram alone.')
      ]
    }
    if args.edit_file:
        scenes = json.loads(args.edit_file.read_text())
    (out / 'edit-manifest.json').write_text(json.dumps(scenes, indent=2))
    for kind, edit in scenes.items():
        if args.only and args.only != kind:
            continue
        parts, srt, vtt, offset = [], [], ['WEBVTT\n'], 0.0
        for i, scene in enumerate(edit):
            prefix = out / f'{kind}-{i:02}'
            bg = prefix.with_suffix('.png')
            x, y, w, h = background(scene, kind, i, len(edit), bg)
            duration = scene['duration']
            source = max(0, scene['source'])
            # Still review panels hold an actual captured app frame. Live panels
            # play the corresponding recording continuously at original speed.
            still = 'live' not in scene and scene['source'] in (ready, answer0, answer1)
            filters = f'[1:v]scale={w}:{h}:flags=lanczos,setsar=1'
            if still:
                image_name = {ready: '01-ready', answer0: 'turn-0-answer', answer1: 'turn-1-answer'}[scene['source']]
                phone_input = ['-loop', '1', '-framerate', '30', '-i', str(run / f'{image_name}.png')]
            else:
                phone_input = ['-ss', str(source), '-i', str(run / 'simulator.mp4')]
            filters += f'[phone];[0:v][phone]overlay={x}:{y}:shortest=1'
            extra_inputs = []
            if 'live' in scene:
                turn = scene['live']
                relevant = [e for e in events if heard[turn] <= e['time'] <= done[turn]]
                lines = []
                for e in relevant:
                    label = None
                    if e['kind'] == 'tool' and e['event']['type'] == 'tool_execution_start':
                        tool = e['event']
                        a = tool.get('args', {})
                        detail = a.get('path') or a.get('pattern') or a.get('query') or ''
                        label = f"{tool.get('toolName', 'tool')}({str(detail)[:72]})"
                    elif e.get('stage') == 'said':
                        label = 'reply complete'
                    elif e['kind'] == 'response':
                        label = 'HTTP response delivered'
                    if label:
                        lines.append((e['time'] - heard[turn], label))
                for j, (t, label) in enumerate(lines[:8]):
                    textfile = out / f'{kind}-{i:02}-event-{j}.txt'
                    textfile.write_text(f'+{t:05.1f}s   {label}')
                    tile = Image.new('RGBA', (1250, 38), (0, 0, 0, 0))
                    ImageDraw.Draw(tile).text((0, 0), textfile.read_text(), font=font(25), fill=INK)
                    tile_path = textfile.with_suffix('.png')
                    tile.save(tile_path)
                    extra_inputs += ['-loop', '1', '-framerate', '30', '-i', str(tile_path)]
                    label = f'base{j}'
                    filters += f"[{label}];[{label}][{j+2}:v]overlay=544:{395+j*39}:enable='gte(t,{t:.3f})':shortest=1"
            filters += '[out]'
            part = prefix.with_suffix('.mp4')
            cmd = ['ffmpeg','-hide_banner','-loglevel','error','-y','-loop','1','-framerate','30','-i',str(bg),
                   *phone_input,*extra_inputs,'-filter_complex',filters,'-map','[out]',
                   '-t',str(duration),'-an','-r','30','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p',str(part)]
            subprocess.run(cmd, check=True)
            parts.append(part)
            text = scene['caption']
            srt.append(f'{i+1}\n{timestamp(offset)} --> {timestamp(offset+duration)}\n{text}\n')
            vtt.append(f'{timestamp(offset,True)} --> {timestamp(offset+duration,True)}\n{text}\n')
            offset += duration
            print(f'{kind}: scene {i+1}/{len(edit)}', flush=True)
        concat = out / f'{kind}-concat.txt'
        concat.write_text('\n'.join(f"file '{p}'" for p in parts))
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(concat),
                        '-c','copy','-movflags','+faststart',str(out/f'{kind}.mp4')],check=True)
        (out/f'{kind}.srt').write_text('\n'.join(srt))
        (out/f'{kind}.vtt').write_text('\n'.join(vtt))
    print(out)


if __name__ == '__main__':
    main()
