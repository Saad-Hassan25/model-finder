#!/usr/bin/env node
import { parseArgs } from 'node:util';
import { createInterface } from 'node:readline/promises';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { realpath } from 'node:fs/promises';
import { AGENTS, LABELS, InstallError, createPlan, publicPlan, applyPlan } from './lib/install.mjs';

const HELP = `Model Finder installer

Run without flags for the guided installer:
  npx --yes github:Saad-Hassan25/model-finder

For agents and automation:
  npx --yes github:Saad-Hassan25/model-finder --agent codex --scope project --yes --json

Options:
  --agent NAME          claude-code (or claude), codex, opencode, all
                        Repeat or use commas to select multiple clients.
  --scope SCOPE         project (current folder) or global (all projects)
  --global, -g          Shorthand for --scope global
  --project-dir PATH    Project folder; defaults to your terminal's directory
  --connections MODE   openrouter (default), both (adds AA), or none
  --login               Start the selected clients' browser sign-in flows
  --no-login            Leave authentication for later (default with --yes)
  --yes, -y             Skip prompts; requires explicit --agent and scope
  --json                JSON result only; never prompts or launches login
  --dry-run             Show the plan without changing files
  --replace             Back up a differing skill before upgrading it
  --help, -h            Show this help

No Python is needed to install. Existing unrelated settings are preserved.
Project scope keeps both the skill and MCP configuration in that project.
OAuth approval and client workspace trust still belong to the user.
`;

export function optionsFrom(argv) {
  const { values } = parseArgs({ args: argv, options: {
    agent: { type: 'string', multiple: true }, scope: { type: 'string' },
    global: { type: 'boolean', short: 'g' }, 'project-dir': { type: 'string' },
    connections: { type: 'string' }, login: { type: 'boolean' }, 'no-login': { type: 'boolean' },
    yes: { type: 'boolean', short: 'y' }, json: { type: 'boolean' },
    'dry-run': { type: 'boolean' }, replace: { type: 'boolean' }, help: { type: 'boolean', short: 'h' },
  } });
  if (values.help) return { help: true };
  const requested = (values.agent || []).flatMap(value => value.split(',')).map(value => value === 'claude' ? 'claude-code' : value);
  if (requested.some(value => value !== 'all' && !AGENTS.includes(value))) throw new InstallError('Unknown agent. Choose claude-code, codex, opencode, or all.');
  const agents = AGENTS.filter(value => requested.includes('all') || requested.includes(value));
  if (values.global && values.scope && values.scope !== 'global') throw new InstallError('--global conflicts with --scope project.');
  const scope = values.global ? 'global' : values.scope;
  if (scope && !['project', 'global'].includes(scope)) throw new InstallError('Scope must be project or global.');
  if (scope === 'global' && values['project-dir']) throw new InstallError('--project-dir only applies to project scope.');
  if (values.connections && !['openrouter', 'both', 'none'].includes(values.connections)) throw new InstallError('Connections must be openrouter, both, or none.');
  if (values.login && (values['no-login'] || values.json)) throw new InstallError('--login cannot be combined with --no-login or --json.');
  return { agents, scope, projectDir: values['project-dir'], connections: values.connections,
    login: Boolean(values.login), noLogin: Boolean(values['no-login']),
    yes: Boolean(values.yes), json: Boolean(values.json), dryRun: Boolean(values['dry-run']), replace: Boolean(values.replace) };
}

async function promptOptions(options, terminal, write) {
  if (!options.agents.length) {
    write('\nInstall for which coding clients?\n  1. Claude Code\n  2. Codex\n  3. OpenCode\n  4. All three\n');
    while (true) {
      const answer = (await terminal.question('Choose numbers, separated by commas: ')).trim();
      const choices = answer.split(',').map(value => value.trim());
      if (choices.length && choices.every(value => ['1', '2', '3', '4'].includes(value))) {
        options.agents = AGENTS.filter((_, index) => choices.includes('4') || choices.includes(String(index + 1)));
        break;
      }
      write('Choose 1, 2, 3, or 4; for example 1,2.\n');
    }
  }
  if (!options.scope) {
    write(`\nWhere should it be available?\n  1. This project: ${path.resolve(options.projectDir || process.cwd())}\n  2. All projects for your user\n`);
    while (true) {
      const answer = (await terminal.question('Choose [1]: ')).trim() || '1';
      if (['1', '2'].includes(answer)) { options.scope = answer === '1' ? 'project' : 'global'; break; }
    }
  }
  if (options.scope === 'global' && options.projectDir) throw new InstallError('--project-dir only applies to project scope.');
  if (!options.connections) {
    write('\nConnect research data?\n  1. OpenRouter (recommended)\n  2. OpenRouter + Artificial Analysis\n  3. Skill only; use existing data access\n');
    while (true) {
      const answer = (await terminal.question('Choose [1]: ')).trim() || '1';
      if (['1', '2', '3'].includes(answer)) { options.connections = { 1: 'openrouter', 2: 'both', 3: 'none' }[answer]; break; }
    }
  }
  if (options.connections !== 'none' && !options.login && !options.noLogin && !options.dryRun) {
    const answer = (await terminal.question('\nOpen the browser sign-in flow after installing? [Y/n]: ')).trim().toLowerCase();
    options.login = !['n', 'no'].includes(answer);
  }
}

function describe(plan, write) {
  write(`\n${plan.scope === 'project' ? 'Project' : 'All-project'} installation\n`);
  for (const item of plan.skills) write(`  ${LABELS[item.agent]}: ${item.action} ${item.path}\n`);
  for (const item of plan.configs) write(`  MCP settings: ${item.action} ${item.path}\n`);
}

export function authenticate(plan, runner = spawnSync) {
  for (const auth of plan.authentication) {
    // All command names and arguments originate from our allowlists, never user
    // text or paths. Windows uses the shell to resolve npm's .cmd client shims.
    const result = runner(auth.command, auth.args, { stdio: 'inherit', cwd: auth.cwd, shell: process.platform === 'win32' });
    auth.state = result.status === 0 && !result.error ? 'authenticated' : 'pending';
  }
}

function nextSteps(plan, write) {
  write('\nModel Finder is installed. Open a new session in your coding client.\n');
  for (const agent of plan.agents) {
    const invocation = { 'claude-code': '/model-finder', codex: '$model-finder', opencode: 'Use the model-finder skill.' }[agent];
    write(`  ${LABELS[agent]}: ${invocation} Find the best-value model for my task.\n`);
  }
  const pending = plan.authentication.filter(auth => auth.state === 'pending');
  if (pending.length) {
    write('\nAuthentication still needs to be completed. Run from the selected project (or use your client MCP settings):\n');
    for (const auth of pending) write(`  ${auth.command} ${auth.args.join(' ')}\n`);
  }
  if (plan.scope === 'project') write('\nYour client may ask you to trust this project or enable its MCP servers.\n');
}

export async function run(argv = process.argv.slice(2), context = {}) {
  const write = context.write || (text => process.stdout.write(text));
  let terminal;
  try {
    const options = optionsFrom(argv);
    if (options.help) { write(HELP); return 0; }
    const interactive = !options.yes && !options.json && Boolean(context.isTTY ?? process.stdin.isTTY);
    if (!interactive && (!options.agents.length || !options.scope)) {
      throw new InstallError('Non-interactive setup needs --agent and --scope (project or global). Use --yes --json for agents.');
    }
    if (interactive) {
      write('\nMODEL FINDER\nChoose your clients, scope, and data connections.\n');
      terminal = context.terminal || createInterface({ input: process.stdin, output: process.stdout });
      await promptOptions(options, terminal, write);
    }
    options.connections ||= 'openrouter';
    const plan = await createPlan(options, context);
    if (!options.json) describe(plan, write);
    if (interactive && !options.dryRun) {
      const answer = (await terminal.question('\nInstall with these settings? [Y/n]: ')).trim().toLowerCase();
      if (['n', 'no'].includes(answer)) { write('Cancelled; no files changed.\n'); return 0; }
    }
    terminal?.close();
    terminal = null;
    if (!options.dryRun) {
      await applyPlan(plan);
      if (options.login) authenticate(plan, context.runner);
    }
    if (options.json) write(JSON.stringify({ ok: true, dry_run: options.dryRun, ...publicPlan(plan) }, null, 2) + '\n');
    else if (options.dryRun) write('\nDry run; no files changed.\n');
    else nextSteps(plan, write);
    return 0;
  } catch (error) {
    const message = error instanceof InstallError || error.code?.startsWith('ERR_PARSE_ARGS')
      ? error.message : `Setup stopped (${error.code || 'unexpected error'}). No credentials were printed.`;
    if (argv.includes('--json')) write(JSON.stringify({ ok: false, error: message, completed: error.completed || [] }) + '\n');
    else write(`\nmodel-finder-install: ${message}\n`);
    return 1;
  } finally { terminal?.close(); }
}

if (process.argv[1] && await realpath(path.resolve(process.argv[1])).catch(() => null) === fileURLToPath(import.meta.url)) {
  process.exitCode = await run();
}
