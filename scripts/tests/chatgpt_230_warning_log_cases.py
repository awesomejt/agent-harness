#!/usr/bin/env python3
"""Self-contained D095 adversarial fixtures; no runtime/public checkout/state access."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments'))
import chatgpt_230_warning_log as helper

EXPECTED = {
    'SERVER': ['serve', '--stdio', '--hostname', '127.0.0.1', '--port', '1234'],
    'DEBUG_CONFIG': ['debug', 'config', '--server', 'http://127.0.0.1:1234'],
    'DEBUG_AGENTS': ['debug', 'agents', '--server', 'http://127.0.0.1:1234'],
}
TARGETS = {'/owned/repo': 'PARENT_REPO', '/owned/config.json': 'OTHER_OWNED'}
WINDOWS = {name: (1767225590.0, 1767225610.0) for name in EXPECTED}
STAMP = '2026-01-01T00:00:04.000Z'


def line(**fields):
    # logging.ts first formats non-string values to strings, then JSON-quotes
    # any value containing whitespace, quotes, '=' or backslashes.
    def value(item):
        text = item if isinstance(item, str) else json.dumps(item, separators=(',', ':'))
        return json.dumps(text) if any(c.isspace() or c in '= "\\' for c in text) else text
    return ' '.join(key + '=' + value(item) for key, item in fields.items())


def clean_rows():
    return [
        line(timestamp='2026-01-01T00:00:00.000Z', level='INFO', run='11111111', message='cli starting', version='2.3.0', channel='latest', args=EXPECTED['SERVER'], role='cli'),
        line(timestamp='2026-01-01T00:00:01.000Z', level='INFO', run='11111111', message='ready', role='server'),
        line(timestamp='2026-01-01T00:00:02.000Z', level='INFO', run='22222222', message='cli starting', version='2.3.0', channel='latest', args=EXPECTED['DEBUG_CONFIG'], role='cli'),
        line(timestamp='2026-01-01T00:00:03.000Z', level='INFO', run='33333333', message='cli starting', version='2.3.0', channel='latest', args=EXPECTED['DEBUG_AGENTS'], role='cli'),
    ]


def encoded(rows):
    return ('\n'.join(rows) + '\n').encode()


def classify(rows):
    return helper.classify(encoded(rows), EXPECTED, TARGETS, windows=WINDOWS)


def warning(message='failed to watch directory', **fields):
    return line(**dict(dict(timestamp=STAMP, level='ERROR', run='11111111',
                            message=message, role='server'), **fields))


def rejects(action):
    try:
        action()
    except helper.Refusal as error:
        assert 'SECRET' not in str(error)
        return
    raise AssertionError('unsafe log accepted')


def main():
    rows = clean_rows()
    assert classify(rows) == {'processes': 3, 'records': 4, 'warnings': []}
    assert classify(list(reversed(rows)))['warnings'] == []  # Complete attribution map, not line order.
    event = warning(path='/owned/repo', cause='SECRET_CAUSE', error='SECRET_ERROR',
                    extra='SECRET_DYNAMIC', stack='SECRET_STACK')
    result = classify(rows + [event, event])
    assert result['warnings'] == [{'process': 'SERVER', 'family': 'WATCH_START', 'target': 'PARENT_REPO', 'count': 2}]
    assert not any(value in repr(result) for value in ('SECRET', '/owned', '11111111'))
    for label, run in (('DEBUG_CONFIG', '22222222'), ('DEBUG_AGENTS', '33333333')):
        result = classify(rows + [warning('cli process failed', run=run, role='cli', cause='SECRET')])
        assert result['warnings'] == [{'process': label, 'family': 'CLI_FAILURE', 'target': 'NONE', 'count': 1}]
    assert classify(rows + [warning('watcher callback failed')])['warnings'][0]['target'] == 'NONE'
    assert classify(rows + [warning('watcher callback failed', path='/owned/repo')])['warnings'][0]['target'] == 'PARENT_REPO'
    rejects(lambda: classify(rows + [warning('watcher callback failed', path='/outside/SECRET')]))
    rejects(lambda: classify(rows + [warning('config file reference is missing or unreadable', level='WARN', path='/outside/SECRET')]))
    assert classify(rows + [warning('config file reference is missing or unreadable', level='WARN', path='/owned/config.json')])['warnings'][0]['target'] == 'OTHER_OWNED'

    for message in ('configuration normalization diagnostic', 'failed to convert managed preferences'):
        rejects(lambda message=message: classify(rows+[warning(message, level='WARN', source='/outside/SECRET')]))
        assert classify(rows+[warning(message, level='WARN', source='/owned/config.json')])['warnings'][0]['target']=='OTHER_OWNED'
    assert classify(rows+[warning('configuration normalization diagnostic', level='WARN', source='OPENCODE_CONFIG_CONTENT')])['warnings'][0]['target']=='NONE'
    escaped = classify(rows+[warning('cli process failed', cause='SECRET\nSECOND_LINE')])
    assert escaped['warnings'][0]['family']=='CLI_FAILURE' and 'SECRET' not in repr(escaped)

    malformed = [b'', encoded(rows)[:-1], b'\xff\n', b'level=INFO level=ERROR\n', b'level=INFO\r\n',
                 b'message="bad\\q"\n', b'message="SECRET\nVALUE"\n', b'message=x\trole=y\n',
                 b'message="truncated\n', b'message=ok trailing\n', b'message=ok \n',
                 b'message=x\x00\n', b'x' * (helper.LIMIT+1)]
    for raw in malformed:
        rejects(lambda raw=raw: helper.classify(raw, EXPECTED, TARGETS, windows=WINDOWS))
    rejects(lambda: helper.parse(b'x'*(helper.MAX_LINE+1)+b'\n'))
    rejects(lambda: helper.parse(b'x=y\n'*(helper.MAX_RECORDS+1)))
    variants = [rows[:-1], rows+[rows[0]],
                rows+[line(timestamp=STAMP,level='INFO',run='44444444',message='cli starting',version='2.3.0',channel='latest',args=['debug','paths'],role='cli')], [row.replace('22222222','11111111') for row in rows],
                [row.replace('channel=latest','channel=SECRET') for row in rows],
                [row.replace('version=2.3.0','version=0.0.0') for row in rows],
                [row.replace('role=server','role=cli') for row in rows],
                rows+[warning('SECRET_UNKNOWN')], rows+[warning(level='WARN', path='/owned/repo')],
                rows+[warning(path='/outside/SECRET')], rows+[warning(path='/owned/repo', run='44444444')],
                rows+[warning(path='/owned/repo', role='unknown')], rows+[warning(path='/owned/repo', timestamp='2026-01-01T00:01:00.000Z')],
                rows+[warning(path='/owned/repo', timestamp='2026-01-01T00:00:04')],
                rows+[warning(path='/owned/repo', level='FATAL')]]
    # Direct array/object values in consumed scalar fields must be static refusals.
    for key in ('level', 'run', 'message', 'role', 'path', 'timestamp'):
        for value in ('[]','{}'):
            event = warning(path='/owned/repo')
            parsed = helper.parse((event+'\n').encode())[0]
            prefix = line(**{k:v for k,v in parsed.items() if k!=key})
            variants.append(rows+[prefix+' '+key+'='+value])
    for variant in variants:
        rejects(lambda variant=variant: classify(variant))

    with tempfile.TemporaryDirectory(prefix='ah-warning-log-') as directory:
        parent = Path(directory).resolve()
        work = parent/'work'
        work.mkdir(mode=0o700)
        path = work/'owned.log'
        data = encoded(rows)
        path.write_bytes(data)
        assert helper.read_log(path,work)==data
        original_read = os.read
        with patch.object(helper.os,'read',side_effect=lambda fd,count: original_read(fd,min(count,7))):
            assert helper.read_log(path,work)==data
        with patch.object(helper.os,'read',return_value=b''):
            rejects(lambda: helper.read_log(path,work))
        original_stat = os.stat
        def changed(name,*args,**kwargs):
            value = original_stat(name,*args,**kwargs)
            if name=='owned.log' and kwargs.get('dir_fd') is not None:
                return SimpleNamespace(**dict({k:getattr(value,k) for k in ('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns')}, st_ino=value.st_ino+1))
            return value
        with patch.object(helper.os,'stat',side_effect=changed):
            rejects(lambda: helper.read_log(path,work))
        outside = parent/'outside.log'
        outside.write_bytes(data)
        link=work/'link.log';link.symlink_to(path)
        rejects(lambda: helper.read_log(link,work))
        nested=work/'nested';nested.symlink_to(parent)
        rejects(lambda: helper.read_log(nested/'outside.log',work))
        hard=work/'hard.log';os.link(path,hard)
        rejects(lambda: helper.read_log(hard,work))
        hard.unlink()
        fifo=work/'fifo.log';os.mkfifo(fifo)
        rejects(lambda: helper.read_log(fifo,work))
        rejects(lambda: helper.read_log(work,work))
        huge=work/'huge.log';huge.write_bytes(b'x'*(helper.LIMIT+1))
        rejects(lambda: helper.read_log(huge,work))
        rejects(lambda: helper.read_log(work/'..'/'outside.log',work))
        rejects(lambda: helper.read_log(outside,work))
        rejects(lambda: helper.read_log(work/'missing',work))

        # Source verifier fixtures are self-contained; no /tmp checkout needed.
        packages=parent/'packages';packages.mkdir()
        fixture=packages/'fixture.ts'
        source='\n'.join('Effect.log'+('Warning' if severity=='WARN' else 'Error')+'('+json.dumps(message)+')'
                         for severity,message in helper.MESSAGES).encode()
        def verify(data):
            fixture.write_bytes(data)
            manifest={'files':{'fixture.ts':hashlib.sha256(data).hexdigest()}}
            with patch.object(Path,'read_text',return_value=json.dumps(manifest)):
                return helper.verify_messages(packages)
        assert verify(source)=={'files':1,'messages':len(helper.MESSAGES)}
        rejects(lambda: verify(source.replace(b'Effect.logError("failed to watch directory")',
                                              b'Effect.logWarning("failed to watch directory")')))
        rejects(lambda: verify(source.replace(b'failed to watch directory',b'SECRET_UNKNOWN')))
    print('PASS: strict D095 parsing, source tuples, provenance/secrets, counts, file links/bounds/shortreads/races')


if __name__=='__main__':
    main()
