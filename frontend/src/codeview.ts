/**
 * Python code panel shown on the right of a visualization.
 *
 * The backend sends plain Python where some lines end with a marker like
 * `#@pop` or `#@case1,case2`. Every algorithm step carries a `code` tag, and
 * the panel highlights the line(s) with that tag. The markers are not shown.
 */

const KEYWORDS = new Set([
  "def", "return", "if", "elif", "else", "while", "for", "in", "not", "and", "or", "is",
  "None", "True", "False", "import", "from", "as", "continue", "break", "raise", "lambda", "pass",
]);
const BUILTINS = new Set(["len", "range", "set", "dict", "list", "float", "min", "max", "any", "reversed", "ValueError"]);

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/** Very small Python highlighter: comments, strings, numbers, keywords, function names */
function highlightPython(line: string): string {
  const out: string[] = [];
  const re = /(#.*$)|("[^"]*"|'[^']*')|(\b\d+(?:\.\d+)?\b)|([A-Za-z_]\w*)|(\s+)|(.)/g;
  let m: RegExpExecArray | null;
  let prevWord = "";
  while ((m = re.exec(line)) !== null) {
    const [tok, comment, str, num, word] = m;
    if (comment) out.push(`<span class="tok-comment">${escapeHtml(comment)}</span>`);
    else if (str) out.push(`<span class="tok-string">${escapeHtml(str)}</span>`);
    else if (num) out.push(`<span class="tok-number">${num}</span>`);
    else if (word) {
      if (KEYWORDS.has(word)) out.push(`<span class="tok-keyword">${word}</span>`);
      else if (prevWord === "def") out.push(`<span class="tok-def">${word}</span>`);
      else if (BUILTINS.has(word)) out.push(`<span class="tok-builtin">${word}</span>`);
      else out.push(escapeHtml(word));
      prevWord = word;
      continue;
    } else out.push(escapeHtml(tok));
    if (tok.trim()) prevWord = "";
  }
  return out.join("");
}

export class CodePanel {
  private tagLines = new Map<string, number[]>();
  private lines: HTMLLIElement[] = [];

  constructor(
    private readonly title: HTMLElement,
    private readonly body: HTMLElement,
    private readonly placeholder = "Run an operation to see its Python code here.",
  ) {
    this.clear();
  }

  clear(): void {
    this.title.textContent = "Python code";
    this.body.innerHTML = `<p class="code-empty">${this.placeholder}</p>`;
    this.tagLines.clear();
    this.lines = [];
  }

  /** Show a new code snippet */
  set(code: string, title: string): void {
    if (!code) {
      this.clear();
      return;
    }
    this.title.textContent = `Python · ${title}`;
    this.tagLines.clear();
    const ol = document.createElement("ol");
    ol.className = "code-lines";
    this.lines = code.replace(/\n$/, "").split("\n").map((raw, i) => {
      const marker = raw.match(/\s*#@([\w,]+)\s*$/);
      let text = raw;
      if (marker) {
        text = raw.slice(0, marker.index).replace(/\s+$/, "");
        for (const tag of marker[1].split(",")) {
          const list = this.tagLines.get(tag) ?? [];
          list.push(i);
          this.tagLines.set(tag, list);
        }
      }
      const li = document.createElement("li");
      li.innerHTML = highlightPython(text) || "&nbsp;";
      ol.append(li);
      return li;
    });
    this.body.innerHTML = "";
    this.body.append(ol);
  }

  /** Highlight the line(s) of the step's code tag */
  highlight(tag: string | null | undefined): void {
    this.lines.forEach((li) => li.classList.remove("hl"));
    if (!tag) return;
    const idx = this.tagLines.get(tag) ?? [];
    idx.forEach((i) => this.lines[i]?.classList.add("hl"));
    const first = this.lines[idx[0]];
    if (first) {
      // scroll inside the code box only (never the page)
      const box = this.body;
      const top = first.offsetTop; // .code-body is position: relative
      if (top < box.scrollTop + 8 || top > box.scrollTop + box.clientHeight - 40) {
        box.scrollTop = Math.max(0, top - box.clientHeight / 3);
      }
    }
  }
}
