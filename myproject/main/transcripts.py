"""Parse uploaded SRT/WebVTT files and normalize them for playback and search."""
import html
import re


_TIMING = re.compile(
    r'(?P<start>(?:\d+:)?\d{2}:\d{2}[.,]\d{3})\s+-->\s+'
    r'(?P<end>(?:\d+:)?\d{2}:\d{2}[.,]\d{3})(?:\s+.*)?$'
)
_TAG = re.compile(r'<[^>]*>')


def _milliseconds(timestamp):
    hours, minutes, seconds = 0, 0, 0
    timestamp = timestamp.replace(',', '.')
    parts = timestamp.split(':')
    if len(parts) == 2:
        minutes = int(parts[0])
        seconds_part = parts[1]
    else:
        hours, minutes = int(parts[0]), int(parts[1])
        seconds_part = parts[2]
    seconds, millis = seconds_part.split('.')
    return ((hours * 60 + minutes) * 60 + int(seconds)) * 1000 + int(millis)


def parse_subtitle_text(source):
    lines = source.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    cues = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.upper() == 'WEBVTT' or line.startswith(('NOTE', 'STYLE', 'REGION')):
            i += 1
            continue
        match = _TIMING.match(line)
        if not match:
            i += 1  # SRT sequence number or optional WebVTT cue identifier.
            continue
        start = _milliseconds(match.group('start'))
        end = _milliseconds(match.group('end'))
        i += 1
        text_lines = []
        while i < len(lines) and lines[i].strip():
            text_lines.append(lines[i].strip())
            i += 1
        text = html.unescape(_TAG.sub('', ' '.join(text_lines))).strip()
        if text and end >= start:
            cues.append({'start_milliseconds': start, 'end_milliseconds': end, 'text': text})
    if not cues:
        raise ValueError('找不到有效字幕片段，請確認檔案是 SRT 或 WebVTT 格式。')
    return cues


def decode_subtitle(data):
    for encoding in ('utf-8-sig', 'cp950'):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError('字幕檔編碼無法辨識，請另存為 UTF-8 後再上傳。')


def cues_to_webvtt(cues):
    def timecode(milliseconds):
        hours, remainder = divmod(int(milliseconds), 3_600_000)
        minutes, remainder = divmod(remainder, 60_000)
        seconds, millis = divmod(remainder, 1000)
        return f'{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}'

    blocks = ['WEBVTT', '']
    for cue in cues:
        blocks.extend([
            f"{timecode(cue['start_milliseconds'])} --> {timecode(cue['end_milliseconds'])}",
            html.escape(cue['text'], quote=False),
            '',
        ])
    return '\n'.join(blocks)
