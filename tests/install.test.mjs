import test from 'node:test';
import assert from 'node:assert/strict';
import * as fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { parse as parseToml } from 'smol-toml';
import { parse as parseJson } from 'jsonc-parser';
import { createPlan, applyPlan, mergeConfig, publicPlan, skillPath, SERVERS } from '../bin/lib/install.mjs';
import { run, optionsFrom, authenticate } from '../bin/install.mjs';

async function sandbox(t) {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'model-finder-test-'));
  t.after(async () => {
    assert.equal(path.dirname(root), path.resolve(os.tmpdir()));
    assert.ok(path.basename(root).startsWith('model-finder-test-'));
    await fs.rm(root, { recursive: true, force: true });
  });
  const project = path.join(root, 'project with spaces');
  const home = path.join(root, 'fake user home');
  await fs.mkdir(project);
  await fs.mkdir(home);
  return { root, project, home, context: { home, env: {} } };
}

function options(projectDir, extra = {}) {
  return { agents: ['codex'], scope: 'project', projectDir, connections: 'openrouter', replace: false, ...extra };
}

test('project scope puts every file inside the chosen project and deduplicates OpenCode', async t => {
  const { project, home, context } = await sandbox(t);
  const plan = await createPlan(options(project, { agents: ['claude-code', 'codex', 'opencode'], connections: 'both' }), context);
  for (const item of [...plan.skills, ...plan.configs]) assert.ok(item.path.startsWith(project + path.sep));
  assert.equal(plan.skills.find(item => item.agent === 'opencode').action, 'reuse');
  await applyPlan(plan);
  assert.deepEqual(await fs.readdir(home), []);
  assert.ok((await fs.readFile(path.join(project, '.agents/skills/model-finder/SKILL.md'), 'utf8')).startsWith('---'));
  assert.equal(JSON.parse(await fs.readFile(path.join(project, '.mcp.json'), 'utf8')).mcpServers.openrouter.url, SERVERS.openrouter);
  assert.equal(parseToml(await fs.readFile(path.join(project, '.codex/config.toml'), 'utf8')).mcp_servers['artificial-analysis'].url, SERVERS['artificial-analysis']);
});

test('global scope respects XDG and Codex home without editing the project', async t => {
  const { project, home } = await sandbox(t);
  const env = { XDG_CONFIG_HOME: path.join(home, 'config'), CODEX_HOME: path.join(home, 'codex-config') };
  const plan = await createPlan(options(project, { agents: ['codex', 'opencode'], scope: 'global' }), { home, env });
  await applyPlan(plan);
  assert.deepEqual(await fs.readdir(project), []);
  assert.equal(plan.configs[0].path, path.join(home, 'codex-config/config.toml'));
  assert.equal(plan.configs[1].path, path.join(home, 'config/opencode/opencode.json'));
  assert.equal(plan.skills[1].path, plan.skills[0].path);
});

test('global Claude MCP uses the user configuration root', async t => {
  const { home, project, context } = await sandbox(t);
  const plan = await createPlan(options(project, { agents: ['claude-code'], scope: 'global' }), context);
  assert.equal(plan.configs[0].path, path.join(home, '.claude.json'));
});

test('custom Claude config directory also relocates its user skill without misleading OpenCode reuse', async t => {
  const { home, project } = await sandbox(t);
  const custom = path.join(home, 'claude-work');
  const plan = await createPlan(options(project, { agents: ['claude-code', 'opencode'], scope: 'global' }),
    { home, env: { CLAUDE_CONFIG_DIR: custom } });
  assert.equal(plan.skills[0].path, path.join(custom, 'skills/model-finder'));
  assert.equal(plan.configs[0].path, path.join(custom, '.claude.json'));
  assert.equal(plan.skills[1].action, 'install');
});

test('JSON updates preserve unrelated settings, credentials, and existing server options', () => {
  const before = JSON.stringify({ theme: 'dark', privateValue: 'SECRET', mcpServers: { existing: { command: 'example' }, openrouter: { type: 'http', url: SERVERS.openrouter, headers: { Authorization: 'SECRET' } } } }, null, 2);
  const after = mergeConfig(before, 'claude-code', ['openrouter', 'artificial-analysis']);
  const parsed = JSON.parse(after);
  assert.equal(parsed.privateValue, 'SECRET');
  assert.equal(parsed.mcpServers.openrouter.headers.Authorization, 'SECRET');
  assert.equal(parsed.mcpServers.existing.command, 'example');
  assert.equal(parsed.mcpServers['artificial-analysis'].type, 'http');
  assert.equal(mergeConfig(after, 'claude-code', ['openrouter', 'artificial-analysis']), after);
});

test('OpenCode JSONC comments, trailing commas, and settings survive the merge', () => {
  const before = '{\n  // Preserve this comment\n  "theme": "dark",\n}\n';
  const after = mergeConfig(before, 'opencode', ['openrouter'], true);
  assert.ok(after.includes('// Preserve this comment'));
  assert.equal(parseJson(after).theme, 'dark');
  assert.equal(parseJson(after).mcp.openrouter.type, 'remote');
});

test('TOML comments and unrelated tables remain intact; both server entries are valid', () => {
  const before = '# Keep my setup\nmodel = "my-model"\n\n[mcp_servers.existing]\ncommand = "other"\n';
  const after = mergeConfig(before, 'codex', ['openrouter', 'artificial-analysis']);
  assert.ok(after.startsWith(before.trimEnd()));
  assert.equal(parseToml(after).model, 'my-model');
  assert.equal(parseToml(after).mcp_servers.existing.command, 'other');
  assert.equal(parseToml(after).mcp_servers.openrouter.url, SERVERS.openrouter);
  assert.equal(mergeConfig(after, 'codex', ['openrouter', 'artificial-analysis']), after);
});

test('conflicting or disabled source definitions are never overwritten', () => {
  for (const entry of [{ type: 'http', url: 'https://other.example/mcp' }, { type: 'http', url: SERVERS.openrouter, disabled: true }]) {
    assert.throws(() => mergeConfig(JSON.stringify({ mcpServers: { openrouter: entry } }), 'claude-code', ['openrouter']), /left unchanged/);
  }
});

test('invalid or incompatible TOML/JSON fails without leaking input content', () => {
  for (const [text, agent] of [['{ SECRET', 'claude-code'], ['key = "SECRET', 'codex']]) {
    assert.throws(() => mergeConfig(text, agent, ['openrouter']), error => !error.message.includes('SECRET'));
  }
  assert.throws(() => mergeConfig('mcp_servers = {}', 'codex', ['openrouter']), /TOML layout/);
});

test('a later-client config conflict aborts all expected writes during preflight', async t => {
  const { project, context } = await sandbox(t);
  await fs.mkdir(path.join(project, '.codex'));
  await fs.writeFile(path.join(project, '.codex/config.toml'), '[mcp_servers.openrouter]\nurl="https://other.example"\n');
  await assert.rejects(createPlan(options(project, { agents: ['claude-code', 'codex'] }), context), /differs/);
  await assert.rejects(fs.stat(path.join(project, '.claude')), { code: 'ENOENT' });
});

test('idempotent install reuses files and does not rewrite config or create backups', async t => {
  const { project, context } = await sandbox(t);
  await applyPlan(await createPlan(options(project), context));
  const plan = await createPlan(options(project), context);
  assert.equal(plan.skills[0].action, 'unchanged');
  assert.equal(plan.configs[0].action, 'unchanged');
  await applyPlan(plan);
  assert.equal(plan.configs[0].backup, undefined);
});

test('an identical skill-manager symlink is reused without replacing its link', async t => {
  const { root, project, context } = await sandbox(t);
  const managed = path.join(root, 'managed-skill');
  const source = fileURLToPath(new URL('../skills/model-finder/', import.meta.url));
  await fs.cp(source, managed, { recursive: true });
  const target = skillPath('codex', 'project', project, context.home);
  await fs.mkdir(path.dirname(target), { recursive: true });
  await fs.symlink(managed, target, process.platform === 'win32' ? 'junction' : 'dir');
  const plan = await createPlan(options(project), context);
  assert.equal(plan.skills[0].action, 'unchanged');
  await applyPlan(plan);
  assert.equal((await fs.lstat(target)).isSymbolicLink(), true);
  await fs.writeFile(path.join(managed, 'SKILL.md'), 'different content');
  await assert.rejects(createPlan(options(project, { replace: true }), context), /original skill manager/);
});

test('upgrading a different skill requires --replace and keeps the entire old copy', async t => {
  const { project, context } = await sandbox(t);
  const target = skillPath('codex', 'project', project, context.home);
  await fs.mkdir(target, { recursive: true });
  await fs.writeFile(path.join(target, 'SKILL.md'), 'personal edits');
  await assert.rejects(createPlan(options(project), context), /--replace/);
  const plan = await createPlan(options(project, { replace: true }), context);
  await applyPlan(plan);
  assert.equal(await fs.readFile(path.join(plan.skills[0].backup, 'SKILL.md'), 'utf8'), 'personal edits');
});

test('changed config is backed up and its contents stay out of public JSON', async t => {
  const { project, context } = await sandbox(t);
  const file = path.join(project, '.mcp.json');
  const original = '{"privateValue":"SECRET"}';
  await fs.writeFile(file, original);
  const plan = await createPlan(options(project, { agents: ['claude-code'] }), context);
  await applyPlan(plan);
  assert.equal(await fs.readFile(plan.configs[0].backup, 'utf8'), original);
  assert.ok(!JSON.stringify(publicPlan(plan)).includes('SECRET'));
});

test('a concurrent config edit is preserved and reported as a partial install', async t => {
  const { project, context } = await sandbox(t);
  const plan = await createPlan(options(project), context);
  await fs.mkdir(path.join(project, '.codex'));
  await fs.writeFile(plan.configs[0].path, 'model="new change"\n');
  await assert.rejects(applyPlan(plan), error => error.message.includes('changed while') && error.completed.length === 1);
  assert.equal(await fs.readFile(plan.configs[0].path, 'utf8'), 'model="new change"\n');
});

test('existing OpenCode JSONC is chosen; two active config formats require resolution', async t => {
  const { project, context } = await sandbox(t);
  await fs.writeFile(path.join(project, 'opencode.jsonc'), '{ // keep\n "theme":"dark" }');
  const plan = await createPlan(options(project, { agents: ['opencode'] }), context);
  assert.ok(plan.configs[0].path.endsWith('.jsonc'));
  await fs.writeFile(path.join(project, 'opencode.json'), '{}');
  await assert.rejects(createPlan(options(project, { agents: ['opencode'] }), context), /Both opencode/);
});

test('skill-only mode never plans configuration or authentication', async t => {
  const { project, context } = await sandbox(t);
  const plan = await createPlan(options(project, { connections: 'none' }), context);
  assert.deepEqual(plan.configs, []);
  assert.deepEqual(plan.authentication, []);
});

test('agent JSON mode installs without prompts or browser authentication', async t => {
  const { project, context } = await sandbox(t);
  let output = '';
  const code = await run(['--agent', 'codex', '--scope', 'project', '--project-dir', project, '--yes', '--json'],
    { ...context, write: text => { output += text; }, runner: () => assert.fail('No login allowed') });
  assert.equal(code, 0);
  const result = JSON.parse(output);
  assert.equal(result.ok, true);
  assert.equal(result.authentication[0].state, 'pending');
  assert.ok((await fs.stat(result.skills[0].path)).isDirectory());
});

test('dry-run JSON changes no files', async t => {
  const { project, home, context } = await sandbox(t);
  let output = '';
  assert.equal(await run(['--agent', 'all', '--scope', 'project', '--project-dir', project, '--dry-run', '--json'],
    { ...context, write: text => { output += text; } }), 0);
  assert.equal(JSON.parse(output).dry_run, true);
  assert.deepEqual(await fs.readdir(project), []);
  assert.deepEqual(await fs.readdir(home), []);
});

test('missing non-interactive choices and unknown options return JSON errors', async () => {
  for (const argv of [['--yes', '--json'], ['--json', '--scope', 'global', '--agent', 'unknown']]) {
    let output = '';
    assert.equal(await run(argv, { isTTY: false, write: text => { output += text; } }), 1);
    assert.equal(JSON.parse(output).ok, false);
  }
});

test('agent flags normalize aliases, repeats, and scope shortcuts', () => {
  assert.deepEqual(optionsFrom(['--agent', 'claude,codex', '--agent', 'opencode', '-g']).agents, ['claude-code', 'codex', 'opencode']);
  assert.equal(optionsFrom(['--agent', 'all', '-g']).scope, 'global');
  assert.throws(() => optionsFrom(['--global', '--scope', 'project']), /conflicts/);
  assert.throws(() => optionsFrom(['--login', '--json']), /cannot/);
  assert.throws(() => optionsFrom(['--scope', 'global', '--project-dir', 'example']), /only applies/);
});

test('wizard gathers agent, scope, data, and sign-in preference and installs', async t => {
  const { project, context } = await sandbox(t);
  const answers = ['2', '1', '1', 'n', 'y'];
  let closed = false;
  const code = await run(['--project-dir', project], { ...context, isTTY: true, write: () => {},
    terminal: { question: async () => answers.shift(), close: () => { closed = true; } } });
  assert.equal(code, 0);
  assert.equal(answers.length, 0);
  assert.equal(closed, true);
  assert.ok((await fs.stat(path.join(project, '.agents/skills/model-finder/SKILL.md'))).isFile());
});

test('wizard cancellation leaves project and home untouched', async t => {
  const { project, home, context } = await sandbox(t);
  const answers = ['n'];
  const code = await run(['--agent', 'codex', '--scope', 'project', '--project-dir', project, '--connections', 'none'],
    { ...context, isTTY: true, write: () => {}, terminal: { question: async () => answers.shift(), close: () => {} } });
  assert.equal(code, 0);
  assert.deepEqual(await fs.readdir(project), []);
  assert.deepEqual(await fs.readdir(home), []);
});

test('authentication uses only fixed client/server tokens and reports failures', async () => {
  const plan = { authentication: [{ agent: 'codex', command: 'codex', args: ['mcp', 'login', 'openrouter'], cwd: os.tmpdir(), state: 'pending' }] };
  authenticate(plan, (command, args) => {
    assert.equal(command, 'codex');
    assert.deepEqual(args, ['mcp', 'login', 'openrouter']);
    return { status: 0 };
  });
  assert.equal(plan.authentication[0].state, 'authenticated');
  authenticate(plan, () => ({ status: 1 }));
  assert.equal(plan.authentication[0].state, 'pending');
});

test('npm allowlist ships the executable and complete skill without caches or local research', () => {
  const root = fileURLToPath(new URL('../', import.meta.url));
  const result = spawnSync('npm', ['pack', '--dry-run', '--json'], {
    cwd: root, encoding: 'utf8', shell: process.platform === 'win32',
  });
  assert.equal(result.status, 0, result.stderr);
  const files = JSON.parse(result.stdout)[0].files.map(item => item.path);
  for (const name of ['bin/install.mjs', 'bin/lib/install.mjs', 'INSTALL.md', 'skills/model-finder/SKILL.md', 'skills/model-finder/scripts/model_finder.py']) {
    assert.ok(files.includes(name), name);
  }
  assert.ok(!files.some(name => /__pycache__|\.pyc$|Initial Work|^\.model-finder\/|^node_modules\//.test(name)));
});

test('the executable runs when launched through a POSIX package-bin symlink', { skip: process.platform === 'win32' }, async t => {
  const { root } = await sandbox(t);
  const entry = fileURLToPath(new URL('../bin/install.mjs', import.meta.url));
  const link = path.join(root, 'linked-installer.mjs');
  await fs.symlink(entry, link);
  const result = spawnSync(process.execPath, [link, '--help'], { encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  assert.ok(result.stdout.includes('Model Finder installer'));
});
