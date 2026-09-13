#!/usr/bin/env python3
"""Check rendered assets and generate a frame contact sheet for human/agent review."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from PIL import Image, ImageDraw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    edit = json.loads((output / 'edit-manifest.json').read_text())
    results = {}
    for kind, scenes in edit.items():
        video = output / f'{kind}.mp4'
        info = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_format', '-show_streams',
                                                  '-of', 'json', str(video)]))
        streams = info['streams']
        assert len(streams) == 1 and streams[0]['codec_type'] == 'video', 'Review should be video-only'
        assert (streams[0]['width'], streams[0]['height']) == (1920, 1080)
        expected = sum(s['duration'] for s in scenes)
        assert abs(float(info['format']['duration']) - expected) < .25, 'Edit duration mismatch'
        assert (output / f'{kind}.srt').read_text().count(' --> ') == len(scenes)
        assert (output / f'{kind}.vtt').read_text().startswith('WEBVTT')
        subprocess.run(['ffmpeg', '-v', 'error', '-i', str(video), '-f', 'null', '-'], check=True)
        sheet = Image.new('RGB', (960, 290 * ((len(scenes) + 1) // 2)), '#151a22')
        draw = ImageDraw.Draw(sheet)
        offset = 0
        for i, scene in enumerate(scenes):
            frame = output / f'{kind}-review-{i:02}.png'
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(offset + scene['duration'] / 2),
                            '-i', str(video), '-frames:v', '1', str(frame)], check=True)
            tile = Image.open(frame).resize((480, 270))
            x, y = i % 2 * 480, i // 2 * 290
            sheet.paste(tile, (x, y))
            draw.text((x + 8, y + 271), f'{i+1}: {scene["title"].replace(chr(10), " ")}', fill='white')
            offset += scene['duration']
        sheet.save(output / f'{kind}-contact-sheet.png')
        results[kind] = {'duration': float(info['format']['duration']), 'dimensions': [1920, 1080],
                         'captions': len(scenes), 'sha256': hashlib.sha256(video.read_bytes()).hexdigest(),
                         'decode': 'passed', 'visual_review': 'contact sheet generated; inspect separately'}
    (output / 'verification.json').write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
