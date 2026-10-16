/**
 * PRACTICE page, three levels:
 *   #/practice                        choose a data structure (Trees, Graphs)
 *   #/practice/<structure>            the tasks of that data structure
 *   #/practice/<structure>/<task>     one task: story, task, rules, input and output
 *
 * Everything comes from the backend: GET /api/practice/ and /api/practice/<task>/.
 */
import { fetchPractice, fetchPracticeTask } from "./api";
import type { PracticeStructure, PracticeTask, PracticeTaskSummary } from "./types";

const box = document.querySelector<HTMLElement>("#practice-content")!;

/** Our own static icons for the data structures */
const ICONS: Record<string, string> = {
  trees: `<svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true">
    <path d="M11 5 L5 16 M11 5 L17 16" stroke="currentColor" stroke-width="1.8" fill="none" />
    <circle cx="11" cy="5" r="3.2" fill="currentColor" /><circle cx="5" cy="16.5" r="3.2" fill="currentColor" />
    <circle cx="17" cy="16.5" r="3.2" fill="currentColor" /></svg>`,
  graphs: `<svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true">
    <path d="M5 6 L16.5 4.5 M5 6 L9 17 M16.5 4.5 L9 17 M16.5 4.5 L18.5 14.5 M9 17 L18.5 14.5"
      stroke="currentColor" stroke-width="1.8" fill="none" />
    <circle cx="5" cy="6" r="3" fill="currentColor" /><circle cx="16.5" cy="4.5" r="3" fill="currentColor" />
    <circle cx="9" cy="17" r="3" fill="currentColor" /><circle cx="18.5" cy="14.5" r="3" fill="currentColor" /></svg>`,
};

let structures: PracticeStructure[] | null = null;
const tasks = new Map<string, PracticeTask>();
let latest = 0; // only the newest navigation is drawn when answers arrive out of order

// ------------------------------------------------------------------ helpers
function h<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  cls = "",
  ...children: (Node | string)[]
): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  e.append(...children);
  return e;
}

function link(href: string, cls: string, ...children: (Node | string)[]): HTMLAnchorElement {
  const a = h("a", cls, ...children);
  a.href = href;
  return a;
}

/** Text with `code` in backticks → text and <code> elements (never parsed as HTML) */
function rich(text: string): DocumentFragment {
  const f = document.createDocumentFragment();
  text.split("`").forEach((part, i) => {
    if (part) f.append(i % 2 ? h("code", "", part) : part);
  });
  return f;
}

function icon(structureId: string): HTMLElement {
  const span = h("span", "pr-icon");
  span.innerHTML = ICONS[structureId] ?? ICONS.trees;
  return span;
}

const count = (n: number) => `${n} ${n === 1 ? "task" : "tasks"}`;
const difficulty = (d: string) => h("span", `pr-diff ${d.toLowerCase()}`, d);
const paragraphs = (items: string[]) => items.map((p) => h("p", "", rich(p)));
const list = (tag: "ul" | "ol", items: string[]) => h(tag, "", ...items.map((i) => h("li", "", rich(i))));
const section = (title: string, ...children: Node[]) => h("section", "pr-section", h("h2", "", title), ...children);

// --------------------------------------------------------------------- page
export async function showPractice(parts: string[]): Promise<void> {
  const mine = ++latest;
  const [structureId, taskId] = parts;
  try {
    if (!structures) {
      box.replaceChildren(h("p", "muted", "Loading the tasks…"));
      structures = await fetchPractice();
    }
    if (mine !== latest) return;
    if (!structureId) return renderChooser(structures);

    const structure = structures.find((s) => s.id === structureId);
    if (!structure) {
      box.replaceChildren(link("#/practice", "pr-back", "← Data structures"), h("p", "error", `There is no data structure '${structureId}' to practise on.`));
      return;
    }
    if (!taskId) return renderTaskList(structure);

    let task = tasks.get(taskId);
    if (!task) {
      box.replaceChildren(backToList(structure), h("p", "muted", "Loading the task…"));
      task = await fetchPracticeTask(taskId);
      tasks.set(taskId, task);
    }
    if (mine !== latest) return;
    renderTask(task, structures.find((s) => s.id === task!.structure) ?? structure);
  } catch (e) {
    if (mine !== latest) return;
    const back = structureId ? link(`#/practice/${structureId}`, "pr-back", "← Back") : null;
    box.replaceChildren(...(back ? [back] : []), h("p", "error", e instanceof Error ? e.message : String(e)));
  }
}

// ------------------------------------------- level 1: choose a data structure
function renderChooser(all: PracticeStructure[]): void {
  box.replaceChildren(
    h("header", "hero", h("h1", "", "Practice"), h("p", "lead", "Choose a data structure, then pick a task.")),
    h(
      "div",
      "pr-grid",
      ...all.map((s) => {
        const card = link(
          `#/practice/${encodeURIComponent(s.id)}`,
          "pr-card pr-structure",
          icon(s.id),
          h("h2", "", s.title),
          h("p", "", s.text),
          h("span", "pr-open", `${count(s.tasks.length)} →`),
        );
        card.dataset.structure = s.id;
        return card;
      }),
    ),
  );
  window.scrollTo(0, 0);
}

// ------------------------------------------------ level 2: its list of tasks
function backToList(s: PracticeStructure): HTMLAnchorElement {
  return link(`#/practice/${encodeURIComponent(s.id)}`, "pr-back", `← ${s.title} tasks`);
}

function renderTaskList(s: PracticeStructure): void {
  const cards = s.tasks.map((t) => taskCard(s, t));
  box.replaceChildren(
    link("#/practice", "pr-back", "← Data structures"),
    h("header", "hero", h("h1", "pr-title", icon(s.id), s.title), h("p", "lead", `${s.text} ${count(s.tasks.length)}.`)),
    cards.length ? h("div", "pr-grid", ...cards) : h("p", "muted", "No tasks here yet."),
  );
  window.scrollTo(0, 0);
}

function taskCard(s: PracticeStructure, t: PracticeTaskSummary): HTMLAnchorElement {
  const card = link(
    `#/practice/${encodeURIComponent(s.id)}/${encodeURIComponent(t.id)}`,
    "pr-card",
    h("span", "pr-topic", t.topic),
    h("h3", "", t.title),
    h("p", "", t.teaser),
    h("span", "pr-meta", difficulty(t.difficulty), h("span", "pr-open", "Open task →")),
  );
  card.dataset.task = t.id;
  return card;
}

// ------------------------------------------------------- level 3: one task
function renderTask(t: PracticeTask, s: PracticeStructure): void {
  const task = section("Your task", ...paragraphs(t.task));
  if (t.task_steps.length) task.append(list("ol", t.task_steps));

  const article = h(
    "article",
    "pr-text",
    h("div", "pr-story", ...paragraphs(t.story)),
    task,
    section("Rules", list("ul", t.rules)),
    section("Input", list("ul", t.input)),
    section("Output", list("ul", t.output)),
  );
  article.dataset.task = t.id;

  box.replaceChildren(
    backToList(s),
    h(
      "header",
      "pr-head",
      h("div", "pr-eyebrow", h("span", "pr-cat", s.title), h("span", "", t.topic), difficulty(t.difficulty)),
      h("h1", "", t.title),
    ),
    article,
  );
  window.scrollTo(0, 0);
}
