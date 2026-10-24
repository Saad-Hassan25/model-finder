import * as fs from 'node:fs/promises';
import path from 'node:path';
import { homedir } from 'node:os';
import { randomUUID } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { parse as parseToml } from 'smol-toml';
import { parse as parseJson, modify, applyEdits } from 'jsonc-parser';

export const ROOT = fileURLToPath(new URL('../../', import.meta.url));
export const SOURCE = path.join(ROOT, 'skills', 'model-finder');
export const SERVERS = {
  openrouter: 'https://mcp.openrouter.ai/mcp',
  'artificial-analysis': 'https://mcp.artificialanalysis.ai/mcp',
};
export const AGENTS = ['claude-code', 'codex', 'opencode'];
export const LABELS = { 'claude-code': 'Claude Code', codex: 'Codex', opencode: 'OpenCode' };

export class InstallError extends Error {}

async function stat(file) {
  try { return await fs.lstat(file); } catch (error) {
    if (error.code === 'ENOENT') return null;
    throw error;
  }
}

export function skillPath(agent, scope, project, home, env = process.env) {
  if (scope === 'project') {
    return path.join(project, { 'claude-code': '.claude', codex: '.agents', opencode: '.opencode' }[agent], 'skills', 'model-finder');
  }
  if (agent === 'opencode') return path.join(env.XDG_CONFIG_HOME || path.join(home, '.config'), 'opencode', 'skills', 'model-finder');
  if (agent === 'claude-code') return path.join(env.CLAUDE_CONFIG_DIR || path.join(home, '.claude'), 'skills', 'model-finder');
  return path.join(home, agent === 'codex' ? '.agents' : '.claude', 'skills', 'model-finder');
}

async function configPath(agent, scope, project, home, env) {
  if (agent === 'claude-code') {
    return scope === 'project' ? path.join(project, '.mcp.json') : path.join(env.CLAUDE_CONFIG_DIR || home, '.claude.json');
  }
  if (agent === 'codex') {
    return path.join(scope === 'project' ? path.join(project, '.codex') : env.CODEX_HOME || path.join(home, '.codex'), 'config.toml');
  }
  const directory = scope === 'project' ? project : path.join(env.XDG_CONFIG_HOME || path.join(home, '.config'), 'opencode');
  const json = path.join(directory, 'opencode.json');
  const jsonc = path.join(directory, 'opencode.jsonc');
  if (await stat(json) && await stat(jsonc)) {
    throw new InstallError('Both opencode.json and opencode.jsonc exist. Consolidate the active MCP settings before running setup.');
  }
  return await stat(jsonc) ? jsonc : json;
}

function object(value) { return value !== null && typeof value === 'object' && !Array.isArray(value); }

function jsonConfig(text, jsonc) {
  const errors = [];
  const parsed = parseJson(text, errors, { allowTrailingComma: jsonc, disallowComments: !jsonc });
  if (errors.length || !object(parsed)) throw new InstallError('Existing JSON configuration is invalid. No configuration was changed.');
  return parsed;
}

function compatible(existing, url, agent) {
  return object(existing) && existing.url === url && existing.enabled !== false && existing.disabled !== true
    && (agent === 'codex' || existing.type === (agent === 'opencode' ? 'remote' : 'http')
      || (agent === 'claude-code' && existing.type === 'streamable-http'));
}

export function mergeConfig(before, agent, servers, jsonc = false) {
  const toml = agent === 'codex';
  let document;
  try { document = toml ? parseToml(before || '') : jsonConfig(before || '{}', jsonc); }
  catch { throw new InstallError('Existing configuration could not be parsed. Fix it before installing; its contents were not printed or changed.'); }
  const key = toml ? 'mcp_servers' : agent === 'opencode' ? 'mcp' : 'mcpServers';
  if (document[key] !== undefined && !object(document[key])) throw new InstallError(`Existing ${key} must be a configuration object.`);
  let after = before || (toml ? '' : '{}\n');
  for (const name of servers) {
    const url = SERVERS[name];
    const existing = document[key]?.[name];
    if (existing !== undefined) {
      if (!compatible(existing, url, agent)) throw new InstallError(`Existing ${name} connection differs or is disabled. It was left unchanged; resolve it or use --connections none.`);
      continue;
    }
    if (toml) {
      after = after.trimEnd() + `\n\n[mcp_servers.${name}]\nurl = "${url}"\n`;
      try { parseToml(after); } catch {
        throw new InstallError('Cannot append the MCP table to this TOML layout. Use the native client setup or --connections none.');
      }
    } else {
      const entry = agent === 'opencode' ? { type: 'remote', url, enabled: true } : { type: 'http', url };
      after = applyEdits(after, modify(after, [key, name], entry, {
        formattingOptions: { insertSpaces: true, tabSize: 2, eol: before?.includes('\r\n') ? '\r\n' : '\n' },
      }));
      jsonConfig(after, jsonc);
    }
  }
  // Identical existing entries, including custom headers, stay byte-for-byte intact.
  return before !== null && servers.every(name => document[key]?.[name] !== undefined) ? before : after;
}

async function files(directory, relative = '') {
  const output = new Map();
  for (const entry of await fs.readdir(path.join(directory, relative), { withFileTypes: true })) {
    if (entry.name === '__pycache__' || entry.name.endsWith('.pyc')) continue;
    const name = path.join(relative, entry.name);
    if (entry.isSymbolicLink()) throw new InstallError('A skill directory contains symbolic links; inspect it before installing.');
    if (entry.isDirectory()) for (const [key, value] of await files(directory, name)) output.set(key, value);
    else if (entry.isFile()) output.set(name, await fs.readFile(path.join(directory, name)));
  }
  return output;
}

async function identical(sourceFiles, directory) {
  const targetFiles = await files(directory);
  return sourceFiles.size === targetFiles.size && [...sourceFiles].every(([name, content]) => targetFiles.has(name) && content.equals(targetFiles.get(name)));
}

export async function createPlan(options, context = {}) {
  const home = path.resolve(context.home || homedir());
  const env = context.env || process.env;
  const project = path.resolve(options.projectDir || process.cwd());
  const source = context.source || SOURCE;
  if (options.scope === 'project' && !(await stat(project))?.isDirectory()) throw new InstallError('The project directory must already exist.');
  const sourceFiles = await files(source);
  if (!sourceFiles.has('SKILL.md')) throw new InstallError('The downloaded package is incomplete: SKILL.md is missing.');
  const plan = { agents: options.agents, scope: options.scope, project, skills: [], configs: [], authentication: [] };
  const plannedPaths = new Set();
  for (const agent of options.agents) {
    let target = skillPath(agent, options.scope, project, home, env);
    let reused = false;
    if (agent === 'opencode') {
      for (const other of ['codex', 'claude-code']) {
        if (other === 'claude-code' && options.scope === 'global' && env.CLAUDE_CONFIG_DIR
          && path.resolve(env.CLAUDE_CONFIG_DIR) !== path.join(home, '.claude')) continue;
        const shared = skillPath(other, options.scope, project, home, env);
        if (options.agents.includes(other) || (await stat(shared))) {
          if (!options.agents.includes(other) && !(await identical(sourceFiles, shared))) {
            throw new InstallError('OpenCode already discovers another model-finder copy. Update that copy or remove the duplicate before installing.');
          }
          target = shared;
          reused = true;
          break;
        }
      }
    }
    const existing = await stat(target);
    if (existing && !existing.isDirectory() && !(existing.isSymbolicLink() && (await fs.stat(target)).isDirectory())) {
      throw new InstallError(`Inspect the existing non-directory before installing: ${target}`);
    }
    const same = existing && await identical(sourceFiles, target);
    if (existing?.isSymbolicLink() && !same) throw new InstallError(`The existing skill is a symlink managed elsewhere: ${target}. Update it with its original skill manager.`);
    if (existing && !same && !options.replace) throw new InstallError(`Skill already exists with different contents: ${target}. Use --replace to back it up and upgrade.`);
    const action = plannedPaths.has(target) || reused ? 'reuse' : same ? 'unchanged' : existing ? 'replace' : 'install';
    plan.skills.push({ agent, path: target, action, source });
    plannedPaths.add(target);
    const servers = options.connections === 'both' ? Object.keys(SERVERS) : options.connections === 'none' ? [] : ['openrouter'];
    if (servers.length) {
      const config = await configPath(agent, options.scope, project, home, env);
      const existingConfig = await stat(config);
      if (existingConfig?.isSymbolicLink() || (existingConfig && !existingConfig.isFile())) throw new InstallError(`Configuration must be a regular file: ${config}`);
      const before = existingConfig ? await fs.readFile(config, 'utf8') : null;
      const after = mergeConfig(before, agent, servers, config.endsWith('.jsonc'));
      plan.configs.push({ agent, path: config, before, after, action: before === after ? 'unchanged' : 'configure' });
      for (const name of servers) plan.authentication.push({ agent, server: name, state: 'pending',
        command: agent === 'claude-code' ? 'claude' : agent,
        args: ['mcp', agent === 'opencode' ? 'auth' : 'login', name],
        cwd: options.scope === 'project' ? project : home });
    }
  }
  return plan;
}

export function publicPlan(plan) {
  return { scope: plan.scope, project: plan.scope === 'project' ? plan.project : null,
    skills: plan.skills.map(({ agent, path, action, backup }) => ({ agent, path, action, ...(backup ? { backup } : {}) })),
    configs: plan.configs.map(({ agent, path, action, backup }) => ({ agent, path, action, ...(backup ? { backup } : {}) })),
    authentication: plan.authentication };
}

async function cleanupStage(directory, parent) {
  const resolved = path.resolve(directory);
  if (path.dirname(resolved) !== path.resolve(parent) || !path.basename(resolved).startsWith('.model-finder-install-')) {
    throw new InstallError('Refused to clean an unexpected staging directory.');
  }
  await fs.rm(resolved, { recursive: true, force: true });
}

export async function applyPlan(plan) {
  const completed = [];
  try {
    for (const skill of plan.skills) {
      if (!['install', 'replace'].includes(skill.action)) continue;
      const parent = path.dirname(skill.path);
      await fs.mkdir(parent, { recursive: true });
      const stage = await fs.mkdtemp(path.join(parent, '.model-finder-install-'));
      try {
        await fs.cp(skill.source, path.join(stage, 'skill'), { recursive: true,
          filter: source => !source.split(path.sep).includes('__pycache__') && !source.endsWith('.pyc') });
        if (skill.action === 'replace') {
          skill.backup = skill.path + '.model-finder-backup-' + randomUUID();
          await fs.rename(skill.path, skill.backup);
        } else if (await stat(skill.path)) throw new InstallError('A destination appeared during installation; rerun setup.');
        try { await fs.rename(path.join(stage, 'skill'), skill.path); }
        catch (error) {
          if (skill.backup) await fs.rename(skill.backup, skill.path);
          throw error;
        }
        completed.push(skill.path);
      } finally { await cleanupStage(stage, parent); }
    }
    for (const config of plan.configs) {
      if (config.action === 'unchanged') continue;
      const current = await stat(config.path) ? await fs.readFile(config.path, 'utf8') : null;
      if (current !== config.before) throw new InstallError('Configuration changed while installing; rerun setup to preserve the new settings.');
      const parent = path.dirname(config.path);
      await fs.mkdir(parent, { recursive: true });
      if (config.before !== null) {
        config.backup = config.path + '.model-finder-backup-' + randomUUID();
        await fs.copyFile(config.path, config.backup, fs.constants.COPYFILE_EXCL);
        await fs.chmod(config.backup, 0o600);
      }
      const stage = await fs.mkdtemp(path.join(parent, '.model-finder-install-'));
      try {
        await fs.writeFile(path.join(stage, 'config'), config.after, { mode: 0o600, flag: 'wx' });
        await fs.rename(path.join(stage, 'config'), config.path);
        completed.push(config.path);
      } finally { await cleanupStage(stage, parent); }
    }
  } catch (error) {
    const failure = new InstallError(error instanceof InstallError ? error.message : `Installation stopped (${error.code || 'filesystem error'}). Rerun after checking filesystem access.`);
    failure.completed = completed;
    throw failure;
  }
}
