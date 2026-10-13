import type { BaseStep } from "./types";

const AUTOPLAY_MS = 1300;

export interface PlayerElements {
  panel: HTMLElement;
  title: HTMLElement;
  counter: HTMLElement;
  message: HTMLElement;
  outcome: HTMLElement;
  list: HTMLOListElement;
  prev: HTMLButtonElement;
  next: HTMLButtonElement;
  play: HTMLButtonElement;
}

/**
 * Walks through the steps returned by the backend: Step 1, Step 2, ...
 * Calls `onStep` every time the shown step changes so the tree can be redrawn.
 */
export class StepPlayer<S extends BaseStep = BaseStep> {
  private steps: S[] = [];
  private index = 0;
  private timer: number | null = null;
  private outcomeText = "";

  constructor(
    private readonly ui: PlayerElements,
    private readonly onStep: (step: S, isLast: boolean) => void,
  ) {
    ui.prev.addEventListener("click", () => this.go(this.index - 1));
    ui.next.addEventListener("click", () => this.go(this.index + 1));
    ui.play.addEventListener("click", () => (this.timer ? this.pause() : this.play()));
  }

  get active(): boolean {
    return this.steps.length > 0;
  }

  load(title: string, steps: S[], outcome: string): void {
    this.pause();
    this.steps = steps;
    this.outcomeText = outcome;
    this.ui.title.textContent = title;
    this.ui.panel.hidden = false;

    this.ui.list.innerHTML = "";
    steps.forEach((step, i) => {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.innerHTML = `<span class="num">Step ${i + 1}</span><span class="txt"></span>`;
      btn.querySelector(".txt")!.textContent = step.message;
      btn.addEventListener("click", () => {
        this.pause();
        this.go(i);
      });
      li.append(btn);
      this.ui.list.append(li);
    });

    this.go(0, true);
  }

  clear(): void {
    this.pause();
    this.steps = [];
    this.ui.panel.hidden = true;
  }

  go(i: number, force = false): void {
    if (!this.steps.length) return;
    const target = Math.max(0, Math.min(this.steps.length - 1, i));
    if (target === this.index && !force) return;
    this.index = target;
    this.update();
  }

  step(delta: number): void {
    this.pause();
    this.go(this.index + delta);
  }

  play(): void {
    if (!this.steps.length) return;
    if (this.index >= this.steps.length - 1) this.go(0);
    this.ui.play.textContent = "❚❚ Pause";
    this.timer = window.setInterval(() => {
      if (this.index >= this.steps.length - 1) this.pause();
      else this.go(this.index + 1);
    }, AUTOPLAY_MS);
  }

  pause(): void {
    if (this.timer !== null) window.clearInterval(this.timer);
    this.timer = null;
    this.ui.play.textContent = "▶ Play";
  }

  private update(): void {
    const step = this.steps[this.index];
    const isLast = this.index === this.steps.length - 1;
    const { ui } = this;

    ui.counter.textContent = `Step ${this.index + 1} of ${this.steps.length}`;
    ui.message.textContent = step.message;
    ui.message.dataset.status = step.status;
    ui.prev.disabled = this.index === 0;
    ui.next.disabled = isLast;

    // The big result badge appears only on the last step
    const finalStatus = this.steps[this.steps.length - 1].status;
    ui.outcome.hidden = !isLast;
    ui.outcome.textContent = this.outcomeText;
    ui.outcome.dataset.status = finalStatus;

    [...ui.list.children].forEach((li, i) => {
      li.classList.toggle("current", i === this.index);
      li.classList.toggle("done", i < this.index);
    });
    // keep the current step visible inside the list without scrolling the page
    const li = ui.list.children[this.index] as HTMLElement | undefined;
    if (li) {
      const top = li.offsetTop; // .steps is position: relative
      if (top < ui.list.scrollTop) ui.list.scrollTop = top;
      else if (top + li.offsetHeight > ui.list.scrollTop + ui.list.clientHeight)
        ui.list.scrollTop = top + li.offsetHeight - ui.list.clientHeight;
    }

    this.onStep(step, isLast);
  }
}
