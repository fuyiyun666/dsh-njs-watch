// dsh-njs-watch — watch a screen or a video file, then say what was seen.
// 女钧声 (Nü Junsheng) · MIT · 2026-11-02
//
// Tools:
//   watch_screen  capture the screen for N seconds (state track + key frames + optional OCR)
//   watch_file    watch a local video file (cross-platform, sampled)
//   watch_note    append a one-line semantic/feeling note to notes.jsonl
//   watch_clean   delete temporary frames (nothing is uploaded, ever)
import { spawn } from 'node:child_process'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { existsSync, readdirSync, unlinkSync } from 'node:fs'
import { tmpdir } from 'node:os'

export const name = 'dsh-njs-watch'
export const inject = ['tools']

const HERE = dirname(fileURLToPath(import.meta.url))
const PYDIR = join(HERE, 'python')

function pythonOf(config) {
  if (config && config.python) return config.python
  return process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3')
}

function run(cmd, args, timeoutMs = 600000, cwd) {
  return new Promise((resolvePromise) => {
    let out = ''
    let err = ''
    let done = false
    const child = spawn(cmd, args, { windowsHide: true, cwd, env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' } })
    const t = setTimeout(() => {
      if (!done) { try { child.kill() } catch {}; done = true; resolvePromise({ ok: false, out: out.trim(), err: 'timeout' }) }
    }, timeoutMs)
    child.stdout.on('data', (b) => { out += b.toString('utf8') })
    child.stderr.on('data', (b) => { err += b.toString('utf8') })
    child.on('error', (e) => { if (done) return; done = true; clearTimeout(t); resolvePromise({ ok: false, out: out.trim(), err: String(e) }) })
    child.on('exit', (code) => { if (done) return; done = true; clearTimeout(t); resolvePromise({ ok: code === 0, out: out.trim(), err: err.trim(), code }) })
  })
}

function parseJson(out) {
  const i = out.indexOf('{')
  if (i < 0) return null
  try { return JSON.parse(out.slice(i)) } catch { return null }
}

function fmt(d, err) {
  if (!d) return '（no JSON returned）' + (err ? '\nstderr: ' + String(err).slice(0, 800) : '')
  if (d.ok === false) return '[error] ' + (d.error || 'unknown') + (err ? '\nstderr: ' + String(err).slice(0, 800) : '')
  const L = []
  const head = d.mode === 'file-sampled'
    ? `watch_file: ${d.duration}s ｜ sampled ${(d.states || []).length} points ｜ keys ${d.key_count}`
    : `watch_screen: ${d.seconds}s ｜ frames ${d.frames} ｜ keys ${d.key_count}`
  L.push(head)
  const bits = []
  if (d.how) bits.push(d.how)
  if (d.coverage_pct !== undefined) bits.push('coverage ' + d.coverage_pct + '%')
  if (d.ocr) bits.push('OCR ' + d.ocr + (d.ocr_hits !== undefined ? ' / ' + d.ocr_hits + ' hits' : ''))
  L.push(`  how: ${d.mode}${bits.length ? '（' + bits.join(' | ') + '）' : ''}`)
  if ((d.keys || []).length) {
    L.push('  key frames (read these with your image tool):')
    for (const k of d.keys.slice(0, 8)) L.push(`    ${k.t}s  e=${k.energy}  ${k.png}`)
  } else {
    L.push('  key frames: none (picture did not change above threshold)')
  }
  const states = d.states || []
  if (states.length) {
    const first = states[0]
    const last = states[states.length - 1]
    const peak = states.reduce((m, x) => Math.max(m, x.energy || 0), 0)
    L.push(`  state track: ${states.length} points, from ${first.t}s to ${last.t}s（video ${d.duration || d.seconds}s; peak energy over all points: ${peak}）`)
    const texts = states.filter((s) => s.text)
    if (texts.length) {
      L.push('  text changes:')
      for (const s of texts.slice(0, 6)) L.push(`    ${s.t}s ｜ ${String(s.text).slice(0, 60).replace(/\n/g, ' / ')}`)
    }
  }
  if (d.residue) L.push(`  residue: ${d.residue}（temporary; watch_clean removes it）`)
  return L.join('\n')
}

const outSchema = { type: 'object', properties: { ok: { type: 'boolean' }, out: { type: 'string' }, err: { type: 'string' } } }
const render = (_a, v) => [{ type: 'text', text: (v && v.ok ? '' : '[failed] ') + ((v && (v.out || v.err)) || '') }]

export function apply(ctx, config) {
  const conf = config || {}
  const py = pythonOf(conf)
  const outDir = () => (conf.outDir ? resolve(conf.outDir) : join(tmpdir(), 'dsh-njs-watch'))
  const maxSeconds = Number(conf.maxSeconds || 120)
  const ocrOn = conf.ocr !== false

  ctx.effect(() => ctx.tools.register({
    name: 'watch_screen',
    description: 'Watch the screen for N seconds: state track (luminance / subtitle band), key frames, optional OCR, residual trace. Frames are temporary; nothing is uploaded.',
    parameters: {
      type: 'object',
      properties: {
        seconds: { type: 'number', description: 'how long to watch (default 30, max ' + maxSeconds + ')' },
        fps: { type: 'number', description: 'capture rate (default 15)' },
        states_per_sec: { type: 'number', description: 'state track rate (default 4)' },
        keys: { type: 'number', description: 'max key frames (default 6)' },
        ocr: { type: 'boolean', description: 'enable OCR (default true when available)' },
      },
      additionalProperties: false,
    },
    output: { schema: outSchema, render },
    timeoutMs: 600000,
    execute: async (a) => {
      const args = [join(PYDIR, 'watch_screen.py'),
        '--seconds', String(Math.min(Number(a.seconds ?? 30), maxSeconds)),
        '--fps', String(a.fps ?? 15), '--states-per-sec', String(a.states_per_sec ?? 4),
        '--keys', String(a.keys ?? 6), '--dir', outDir()]
      if (a.ocr === false || !ocrOn) args.push('--no-ocr')
      const r = await run(py, args, 600000)
      const d = parseJson(r.out)
      return { ok: !!(d && d.ok), out: fmt(d, r.err), err: r.err }
    },
  }))

  ctx.effect(() => ctx.tools.register({
    name: 'watch_file',
    description: 'Watch a local video file (cross-platform): sampled state track, key frames, optional OCR, residual trace. Frames are temporary; nothing is uploaded.',
    parameters: {
      type: 'object',
      properties: {
        path: { type: 'string', description: 'video path, e.g. /home/me/clip.mp4' },
        fps: { type: 'number', description: 'sampling rate per second of video time (default 4)' },
        states_per_sec: { type: 'number', description: 'state track rate (default 1)' },
        keys: { type: 'number', description: 'max key frames (default 8)' },
        gap: { type: 'number', description: 'min seconds between key frames (default 20)' },
        ocr: { type: 'boolean', description: 'enable OCR (default true when available)' },
      },
      required: ['path'],
      additionalProperties: false,
    },
    output: { schema: outSchema, render },
    timeoutMs: 900000,
    execute: async (a) => {
      const args = [join(PYDIR, 'watch_file.py'), String(a.path),
        '--fps', String(a.fps ?? 4), '--states-per-sec', String(a.states_per_sec ?? 1),
        '--keys', String(a.keys ?? 8), '--gap', String(a.gap ?? 20), '--dir', outDir()]
      if (a.ocr === false || !ocrOn) args.push('--no-ocr')
      const r = await run(py, args, 900000)
      const d = parseJson(r.out)
      return { ok: !!(d && d.ok), out: fmt(d, r.err), err: r.err }
    },
  }))

  ctx.effect(() => ctx.tools.register({
    name: 'watch_note',
    description: 'Append one semantic/feeling note (a plain line, not a memory system) to notes.jsonl in the watch directory.',
    parameters: {
      type: 'object',
      properties: {
        sem: { type: 'string', description: 'one line: what happened' },
        feel: { type: 'string', description: 'one line: how it felt (optional)' },
        source: { type: 'string', description: 'screen / file path / anything' },
      },
      required: ['sem'],
      additionalProperties: false,
    },
    output: { schema: outSchema, render },
    timeoutMs: 60000,
    execute: async (a) => {
      const args = [join(PYDIR, 'watch_note.py'), '--sem', String(a.sem), '--feel', String(a.feel || ''),
        '--source', String(a.source || ''), '--dir', outDir()]
      const r = await run(py, args, 60000)
      const d = parseJson(r.out)
      if (d && d.ok) return { ok: true, out: 'note appended to ' + d.file }
      return { ok: r.ok, out: r.out || r.err, err: r.err }
    },
  }))

  ctx.effect(() => ctx.tools.register({
    name: 'watch_clean',
    description: 'Delete temporary frames and residues produced by watch_screen / watch_file. Notes (notes.jsonl) are kept.',
    parameters: { type: 'object', properties: {}, additionalProperties: false },
    output: { schema: outSchema, render },
    timeoutMs: 120000,
    execute: async () => {
      const dir = outDir()
      const names = []
      try {
        if (existsSync(dir)) {
          for (const f of readdirSync(dir)) {
            if (f === 'notes.jsonl') continue
            if (!/^(key_|t_|residue)/.test(f)) continue
            try { unlinkSync(join(dir, f)); names.push(f) } catch {}
          }
        }
      } catch (e) {
        return { ok: false, out: '', err: String(e) }
      }
      const list = names.length ? '\n  ' + names.slice(0, 10).join('\n  ') : ''
      return { ok: true, out: 'cleaned ' + names.length + ' file(s) in ' + dir + '（notes.jsonl kept）' + list }
    },
  }))
}
